#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests unitaires de l'étape 8 : Media Solution (EffectCraft, headless)."""

import importlib.util
import json
from pathlib import Path

import pytest


def _load_step8_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / 'workflow_scripts' / 'step8' / 'run_mediasolution_ec.py'
    spec = importlib.util.spec_from_file_location('workflow_scripts.step8.run_mediasolution_ec', module_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestParsePanelLine:
    def test_total_line(self):
        mod = _load_step8_module()

        # Given: une ligne « Batch démarré » du panel
        line = '[INFO] 12:34:56 | Batch démarré : 12 projet(s) sur 3 dossier(s)'

        # When:  traduction en lignes normalisées
        emitted = mod.parse_panel_line(line)

        # Then:  le backend reçoit le total
        assert emitted == ['MS_BATCH_TOTAL: 12']

    def test_progress_line(self):
        mod = _load_step8_module()

        # Given: une ligne de progression du panel
        line = '[INFO] 12:34:57 | --- 3/12 : clip1.mp4'

        # When:  traduction en lignes normalisées
        emitted = mod.parse_panel_line(line)

        # Then:  la progression est transmise avec le nom de la vidéo
        assert emitted == ['MS_BATCH_PROGRESS: 3/12 - clip1.mp4']

    def test_saved_project_line(self):
        mod = _load_step8_module()

        # Given: une ligne de projet enregistré
        line = '[SUCCESS] 12:35:01 | Projet enregistré : clip1_9x16.ecproj (0.4 s)'

        # When:  traduction en lignes normalisées
        emitted = mod.parse_panel_line(line)

        # Then:  le projet est signalé comme traité
        assert emitted == ['MS_BATCH_OK: clip1_9x16.ecproj']

    def test_unit_error_line(self):
        mod = _load_step8_module()

        # Given: une ligne d'erreur d'unité
        line = '[ERROR] 12:35:02 | Erreur sur clip2.mp4 : import impossible'

        # When:  traduction en lignes normalisées
        emitted = mod.parse_panel_line(line)

        # Then:  l'échec est signalé avec le nom de la vidéo
        assert emitted == ['MS_BATCH_FAIL: clip2.mp4']

    def test_batch_end_line(self):
        mod = _load_step8_module()

        # Given: la ligne de fin de batch
        line = '[SUCCESS] 12:40:00 | Batch terminé : 12/12 projet(s) traité(s)'

        # When:  traduction en lignes normalisées
        emitted = mod.parse_panel_line(line)

        # Then:  le résumé est transmis
        assert emitted == ['MS_BATCH_END: 12/12 projet(s) traité(s)']

    def test_unrelated_line_is_ignored(self):
        mod = _load_step8_module()

        # Given: une ligne quelconque sans motif de progression
        line = '[INFO] 12:34:57 | Traitement 3/12 : clip1.mp4'

        # When:  traduction en lignes normalisées
        emitted = mod.parse_panel_line(line)

        # Then:  aucune ligne parasite n'est émise (seul le préfixe « --- » compte)
        assert emitted == []


class TestBuildDriverJs:
    def test_driver_uses_full_batch_mode_and_escaping(self):
        mod = _load_step8_module()

        # Given: des dossiers dont un contient un guillemet, et une config JSON
        folders = ['/mnt/cache/117 Camille', '/mnt/cache/a"b']
        config_json = json.dumps({'enableCuts': True, 'docsSubFolderName': 'docs'}, ensure_ascii=False)

        # When:  génération du driver
        driver = mod.build_driver_js('// panel', folders, config_json)

        # Then:  le panel est concaténé et le batch complet est piloté (maxUnits = 0)
        assert driver.startswith('// panel')
        assert '"scripting.allowScriptsWriteFiles"' in driver
        assert 'mediasolutionEC.applyConfig(' in driver
        assert json.dumps(folders) in driver
        assert 'JSON.parse(mediasolutionEC.runBatch(JSON.stringify(MS_FOLDERS), null, 0))' in driver
        assert 'MS_BATCH_RESULT: ' in driver
        assert 'throw new Error' in driver

    def test_driver_without_config(self):
        mod = _load_step8_module()

        # Given: aucune config panel disponible
        folders = ['/mnt/cache/117 Camille']

        # When:  génération du driver
        driver = mod.build_driver_js('// panel', folders, None)

        # Then:  aucun appel applyConfig n'est émis
        assert 'applyConfig' not in driver


class TestSelectFolders:
    def test_ignores_missing_folders_and_folders_without_docs(self, tmp_path):
        mod = _load_step8_module()

        # Given: un dossier valide, un sans docs/ et un inexistant
        good = tmp_path / 'good'
        (good / 'docs').mkdir(parents=True)
        without_docs = tmp_path / 'without-docs'
        without_docs.mkdir()
        manifest = {
            'projects': [
                {'name': 'good', 'path': str(good)},
                {'name': 'without-docs', 'path': str(without_docs)},
                {'name': 'missing', 'path': str(tmp_path / 'missing')},
            ]
        }

        # When:  sélection des dossiers à traiter
        folders = mod.select_folders(manifest, [], 'docs')

        # Then:  seul le dossier valide est conservé
        assert folders == [str(good.resolve())]

    def test_manual_folders_short_circuit_manifest(self, tmp_path):
        mod = _load_step8_module()

        # Given: un manifeste et un dossier manuel valide
        manual = tmp_path / 'manual'
        (manual / 'docs').mkdir(parents=True)
        manifest = {'projects': [{'name': 'x', 'path': str(tmp_path / 'missing')}]}

        # When:  sélection avec --folder
        folders = mod.select_folders(manifest, [str(manual)], 'docs')

        # Then:  seul le dossier manuel est retenu
        assert folders == [str(manual.resolve())]


class TestEvaluateResult:
    def test_success(self):
        mod = _load_step8_module()

        # Given / When / Then
        assert mod.evaluate_result({'ok': True, 'errors': []}) is True

    def test_partial_errors_is_failure(self):
        mod = _load_step8_module()

        # Given / When / Then
        assert mod.evaluate_result({'ok': True, 'errors': ['clip : boom']}) is False

    def test_missing_or_ko_result_is_failure(self):
        mod = _load_step8_module()

        # Given / When / Then
        assert mod.evaluate_result(None) is False
        assert mod.evaluate_result({'ok': False, 'error': 'aucun dossier'}) is False


class TestLatestManifest:
    def test_picks_most_recent(self, tmp_path):
        mod = _load_step8_module()

        # Given: deux manifestes d'âges différents
        older = tmp_path / 'finalized_projects_20260101_000000.json'
        newer = tmp_path / 'finalized_projects_20260102_000000.json'
        older.write_text('{}', encoding='utf-8')
        newer.write_text('{}', encoding='utf-8')
        import os
        import time
        now = time.time()
        os.utime(older, (now - 60, now - 60))
        os.utime(newer, (now, now))

        # When:  recherche du manifeste le plus récent
        found = mod.latest_manifest(tmp_path)

        # Then:  le plus récent est retourné
        assert found == newer

    def test_returns_none_without_manifest(self, tmp_path):
        mod = _load_step8_module()

        # Given / When / Then
        assert mod.latest_manifest(tmp_path) is None


class TestMainExitCodes:
    def test_missing_manifest_returns_1(self, tmp_path, monkeypatch):
        mod = _load_step8_module()

        # Given: aucun manifeste de l'étape 7
        monkeypatch.setattr(mod, 'LOG_DIR', tmp_path / 'step8')
        monkeypatch.setattr(mod, 'STEP7_LOG_DIR', tmp_path / 'step7')

        # When:  exécution de l'étape 8
        code = mod.main([])

        # Then:  l'étape échoue explicitement
        assert code == 1

    def test_empty_manifest_returns_0(self, tmp_path, monkeypatch):
        mod = _load_step8_module()

        # Given: un manifeste présent mais sans projet
        monkeypatch.setattr(mod, 'LOG_DIR', tmp_path / 'step8')
        step7_dir = tmp_path / 'step7'
        step7_dir.mkdir()
        monkeypatch.setattr(mod, 'STEP7_LOG_DIR', step7_dir)
        manifest = step7_dir / 'finalized_projects_20260101_000000.json'
        manifest.write_text(
            json.dumps({'schema': 1, 'output_dir': str(tmp_path), 'projects': []}),
            encoding='utf-8',
        )

        # When:  exécution de l'étape 8
        code = mod.main([])

        # Then:  rien à traiter => étape terminée
        assert code == 0

    def test_all_folders_invalid_returns_1(self, tmp_path, monkeypatch):
        mod = _load_step8_module()

        # Given: un manifeste dont tous les dossiers ont disparu
        monkeypatch.setattr(mod, 'LOG_DIR', tmp_path / 'step8')
        step7_dir = tmp_path / 'step7'
        step7_dir.mkdir()
        monkeypatch.setattr(mod, 'STEP7_LOG_DIR', step7_dir)
        manifest = step7_dir / 'finalized_projects_20260101_000000.json'
        manifest.write_text(
            json.dumps({
                'schema': 1,
                'output_dir': str(tmp_path),
                'projects': [{'name': 'gone', 'path': str(tmp_path / 'gone')}],
            }),
            encoding='utf-8',
        )

        # When:  exécution de l'étape 8
        code = mod.main([])

        # Then:  l'étape échoue (dossiers listés mais introuvables)
        assert code == 1


class TestRunCli:
    def _fake_popen(self, lines, returncode=0):
        class FakeProcess:
            def __init__(self):
                self.stdout = iter(lines)
                self.returncode = returncode

            def poll(self):
                return self.returncode

            def wait(self, timeout=None):
                return self.returncode

            def terminate(self):
                pass

            def kill(self):
                pass

        return FakeProcess()

    def test_relays_panel_lines_and_captures_result(self, tmp_path, monkeypatch, capsys):
        mod = _load_step8_module()

        # Given: une sortie CLI simulée (panel + résultat final)
        lines = [
            '[INFO] 12:00:00 | Batch démarré : 1 projet(s) sur 1 dossier(s)\n',
            '[INFO] 12:00:01 | --- 1/1 : clip.mp4\n',
            '[SUCCESS] 12:00:02 | Projet enregistré : clip_9x16.ecproj (0.2 s)\n',
            '[SUCCESS] 12:00:02 | Batch terminé : 1/1 projet(s) traité(s)\n',
            'MS_BATCH_RESULT: {"ok":true,"total":1,"processed":1,"unitIndex":1,"running":false,"errors":[]}\n',
        ]
        monkeypatch.setattr(mod.subprocess, 'Popen', lambda *args, **kwargs: self._fake_popen(lines))

        driver = tmp_path / 'driver.jsx'
        driver.write_text('// driver', encoding='utf-8')

        # When:  exécution du CLI
        code, result = mod.run_cli('/usr/bin/effectcraft-cli', driver, tmp_path)

        # Then:  la sortie est relayée, les lignes normalisées émises et le résultat capturé
        captured = capsys.readouterr().out
        assert '[INFO] 12:00:01 | --- 1/1 : clip.mp4' in captured
        assert 'MS_BATCH_TOTAL: 1' in captured
        assert 'MS_BATCH_PROGRESS: 1/1 - clip.mp4' in captured
        assert 'MS_BATCH_OK: clip_9x16.ecproj' in captured
        assert 'MS_BATCH_END: 1/1 projet(s) traité(s)' in captured
        assert code == 0
        assert result == {
            'ok': True,
            'total': 1,
            'processed': 1,
            'unitIndex': 1,
            'running': False,
            'errors': [],
        }

    def test_bridge_mode_passes_bridge_option(self, tmp_path, monkeypatch):
        mod = _load_step8_module()
        captured = {}

        # Given: un CLI mocké qui note la commande reçue
        def fake_popen(command, **kwargs):
            captured['command'] = command
            return self._fake_popen(
                ['MS_BATCH_RESULT: {"ok":true,"total":0,"processed":0,"unitIndex":0,"running":false,"errors":[]}\n']
            )

        monkeypatch.setattr(mod.subprocess, 'Popen', fake_popen)
        driver = tmp_path / 'driver.jsx'
        driver.write_text('// driver', encoding='utf-8')

        # When:  exécution en mode bridge
        code, result = mod.run_cli('/usr/bin/effectcraft-cli', driver, tmp_path, mode='bridge', bridge_port=9877)

        # Then:  la commande cible le control channel de l'application
        assert captured['command'] == ['/usr/bin/effectcraft-cli', 'script', str(driver), '--bridge', '9877']
        assert code == 0
        assert result == {'ok': True, 'total': 0, 'processed': 0, 'unitIndex': 0, 'running': False, 'errors': []}

    def test_missing_result_line_returns_none(self, tmp_path, monkeypatch, capsys):
        mod = _load_step8_module()

        # Given: une sortie CLI qui n'émet pas MS_BATCH_RESULT
        lines = ['[ERROR] 12:00:00 | crash inattendu\n']
        monkeypatch.setattr(mod.subprocess, 'Popen', lambda *args, **kwargs: self._fake_popen(lines, returncode=1))

        driver = tmp_path / 'driver.jsx'
        driver.write_text('// driver', encoding='utf-8')

        # When:  exécution du CLI
        code, result = mod.run_cli('/usr/bin/effectcraft-cli', driver, tmp_path)

        # Then:  le code retour est remonté et aucun résultat n'est disponible
        assert code == 1
        assert result is None


class TestLoadManifest:
    def test_invalid_manifest_raises(self, tmp_path):
        mod = _load_step8_module()

        # Given: un manifeste qui n'est pas un objet JSON
        manifest = tmp_path / 'finalized_projects_20260101_000000.json'
        manifest.write_text('[]', encoding='utf-8')

        # When / Then:  la validation échoue
        with pytest.raises(ValueError):
            mod.load_manifest(manifest)


class TestExecutionMode:
    """Détection du mode : headless (<= 0.7) ou bridge (0.8+ refuse le headless pur)."""

    def test_version_tuple(self):
        mod = _load_step8_module()

        # Given / When / Then
        assert mod.version_tuple('0.8.1') == (0, 8, 1)
        assert mod.version_tuple('0.7') == (0, 7, 0)

    def test_headless_blocked_from_0_8(self):
        mod = _load_step8_module()

        # Given / When / Then
        assert mod.headless_scripts_blocked('0.7.0') is False
        assert mod.headless_scripts_blocked('0.8.0') is True
        assert mod.headless_scripts_blocked('1.0.0') is True
        assert mod.headless_scripts_blocked(None) is False

    def test_resolve_mode_auto(self, monkeypatch):
        mod = _load_step8_module()

        # Given: une version 0.7 puis 0.8
        monkeypatch.setattr(mod, 'cli_version', lambda _cli: '0.7.0')

        # When / Then:  headless en 0.7
        assert mod.resolve_execution_mode('auto', '/x')[0] == 'headless'

        # Given: 0.8.0
        monkeypatch.setattr(mod, 'cli_version', lambda _cli: '0.8.0')

        # Then:  bridge imposé par le garde-fou de scripting
        assert mod.resolve_execution_mode('auto', '/x')[0] == 'bridge'

    def test_forced_modes_ignore_version(self, monkeypatch):
        mod = _load_step8_module()

        # Given: une version 0.8.0
        monkeypatch.setattr(mod, 'cli_version', lambda _cli: '0.8.0')

        # When / Then:  un mode forcé prime
        assert mod.resolve_execution_mode('headless', '/x')[0] == 'headless'
        monkeypatch.setattr(mod, 'cli_version', lambda _cli: '0.7.0')
        assert mod.resolve_execution_mode('bridge', '/x')[0] == 'bridge'


    def test_bridge_mode_without_app_returns_1(self, tmp_path, monkeypatch):
        mod = _load_step8_module()

        # Given: un projet valide mais aucune instance EffectCraft en écoute
        project = tmp_path / 'ProjetTest'
        (project / 'docs').mkdir(parents=True)
        monkeypatch.setattr(mod, 'LOG_DIR', tmp_path / 'step8')
        monkeypatch.setattr(mod, 'DRIVERS_DIR', tmp_path / 'step8' / 'drivers')
        step7_dir = tmp_path / 'step7'
        step7_dir.mkdir()
        monkeypatch.setattr(mod, 'STEP7_LOG_DIR', step7_dir)
        manifest = step7_dir / 'finalized_projects_20260101_000000.json'
        manifest.write_text(
            json.dumps({
                'schema': 1,
                'output_dir': str(tmp_path),
                'projects': [{'name': 'ProjetTest', 'path': str(project)}],
            }),
            encoding='utf-8',
        )
        monkeypatch.setattr(mod, 'resolve_cli', lambda candidate: '/usr/bin/effectcraft-cli')
        monkeypatch.setattr(mod, 'resolve_execution_mode', lambda forced, cli: ('bridge', '0.8.0'))
        monkeypatch.setattr(mod, 'bridge_port_open', lambda port, timeout=2.0: False)

        def fail_launch(*args, **kwargs):
            raise AssertionError('launch_app ne doit pas être appelée avec --no-launch-app')

        monkeypatch.setattr(mod, 'launch_app', fail_launch)

        # When:  exécution en mode bridge, sans lancement automatique
        code = mod.main(['--mode', 'bridge', '--no-launch-app'])

        # Then:  l'étape échoue avec un message clair (application non lancée)
        assert code == 1

    def test_bridge_mode_launches_app_when_missing(self, tmp_path, monkeypatch):
        mod = _load_step8_module()

        # Given: un projet valide et aucune instance EffectCraft en écoute
        project = tmp_path / 'ProjetTest'
        (project / 'docs').mkdir(parents=True)
        monkeypatch.setattr(mod, 'LOG_DIR', tmp_path / 'step8')
        monkeypatch.setattr(mod, 'DRIVERS_DIR', tmp_path / 'step8' / 'drivers')
        step7_dir = tmp_path / 'step7'
        step7_dir.mkdir()
        monkeypatch.setattr(mod, 'STEP7_LOG_DIR', step7_dir)
        manifest = step7_dir / 'finalized_projects_20260101_000000.json'
        manifest.write_text(
            json.dumps({
                'schema': 1,
                'output_dir': str(tmp_path),
                'projects': [{'name': 'ProjetTest', 'path': str(project)}],
            }),
            encoding='utf-8',
        )
        monkeypatch.setattr(mod, 'resolve_cli', lambda candidate: '/usr/bin/effectcraft-cli')
        monkeypatch.setattr(mod, 'resolve_execution_mode', lambda forced, cli: ('bridge', '0.8.0'))
        monkeypatch.setattr(mod, 'bridge_port_open', lambda port, timeout=2.0: False)
        launched = {}

        def fake_launch(app_path, port, log_path, timeout=60.0):
            launched['app'] = (app_path, port)
            return True

        monkeypatch.setattr(mod, 'launch_app', fake_launch)
        monkeypatch.setattr(mod, 'activate_scripting_preference', lambda cli, port: True)
        monkeypatch.setattr(
            mod,
            'run_cli',
            lambda cli, driver, cwd, mode='headless', bridge_port=None: (0, {'ok': True, 'errors': []}),
        )

        # When:  exécution en mode bridge avec lancement automatique (défaut)
        code = mod.main(['--mode', 'bridge'])

        # Then:  l'application est lancée puis le batch s'exécute
        assert code == 0
        assert launched['app'] == ('/usr/bin/effectcraft-cli', 9877)


class _FakeAppProcess:
    """Process d'application simulé pour les tests de launch_app."""

    def __init__(self, returncode=None):
        self.returncode = returncode

    def poll(self):
        return self.returncode


class TestLaunchApp:
    """Lancement de l'application en mode bridge."""

    def test_starts_application_and_waits_for_channel(self, tmp_path, monkeypatch):
        mod = _load_step8_module()
        captured = {}

        # Given: un process d'application vivant et un control channel qui répond
        def fake_popen(command, **kwargs):
            captured['command'] = command
            return _FakeAppProcess()

        monkeypatch.setattr(mod.subprocess, 'Popen', fake_popen)
        monkeypatch.setattr(mod, 'bridge_port_open', lambda port, timeout=2.0: True)

        # When:  lancement
        ok = mod.launch_app('/usr/bin/effectcraft', 9877, tmp_path / 'launch.log', timeout=5)

        # Then:  application lancée avec son canal, détachée du wrapper
        assert ok is True
        assert captured['command'] == ['/usr/bin/effectcraft', '--control', '9877', '--empty']

    def test_fails_when_process_exits(self, tmp_path, monkeypatch):
        mod = _load_step8_module()

        # Given: une application qui s'arrête au démarrage et aucun canal
        monkeypatch.setattr(mod.subprocess, 'Popen', lambda command, **kwargs: _FakeAppProcess(returncode=1))
        monkeypatch.setattr(mod, 'bridge_port_open', lambda port, timeout=2.0: False)

        # When / Then
        assert mod.launch_app('/usr/bin/effectcraft', 9877, tmp_path / 'launch.log', timeout=5) is False


class TestProgressPatterns:
    """Contrat backend : les patterns STEP8 parsent les lignes MS_BATCH_* émises par le wrapper."""

    def test_configured_patterns_parse_normalized_lines(self):
        from config.workflow_commands import WorkflowCommandsConfig
        from services.workflow_executor import parse_and_update_progress
        from services.workflow_state import get_workflow_state

        # Given: la configuration STEP8 et un état initialisé
        patterns = WorkflowCommandsConfig().get_step_config('STEP8')['progress_patterns']
        state = get_workflow_state()
        state.initialize_all_steps(['STEP8'])
        state_vars = {'current_item_counter': 0, 'completed_items': set()}

        # When:  le parseur backend consomme les lignes normalisées du wrapper
        for line in [
            'MS_BATCH_TOTAL: 2',
            'MS_BATCH_PROGRESS: 1/2 - clip1.mp4',
            'MS_BATCH_OK: clip1_9x16.ecproj',
        ]:
            parse_and_update_progress(line, 'STEP8', patterns, state_vars)

        # Then:  total, progression et texte d'item sont reflétés dans l'état
        assert state.get_step_field('STEP8', 'progress_total') == 2
        assert state.get_step_field('STEP8', 'progress_current') == 1
        assert state.get_step_field('STEP8', 'progress_text') == 'clip1_9x16.ecproj'
