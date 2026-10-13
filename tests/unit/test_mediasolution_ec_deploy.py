"""`deploy.sh` : synchronisation du dépôt vers la copie de travail (~/Media_Solution).

Les tests rejouent le script sur un arbre factice (panel + `install.sh` bouchon, journal et
cache) : ils ne touchent ni `~/Media_Solution` ni la copie installée dans EffectCraft.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "MediaSolution-EC" / "deploy.sh"

pytestmark = pytest.mark.skipif(shutil.which("rsync") is None,
                                reason="rsync requis par deploy.sh")


def run(source: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(source / "deploy.sh"), *args],
                          capture_output=True, text=True)


@pytest.fixture()
def fake_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "tools" / "__pycache__").mkdir(parents=True)
    shutil.copy2(DEPLOY_SCRIPT, source / "deploy.sh")
    (source / "MediaSolution.jsx").write_text("// panel\n", encoding="utf-8")
    (source / "install.sh").write_text("#!/usr/bin/env bash\necho STUB_PANEL\n", encoding="utf-8")
    (source / "install.sh").chmod(0o755)
    (source / "tools" / "outil.py").write_text("print(1)\n", encoding="utf-8")
    (source / "tools" / "export.log").write_text("journal du dépôt\n", encoding="utf-8")
    (source / "tools" / "__pycache__" / "outil.cpython-310.pyc").write_bytes(b"pyc")
    return source


def test_deploy_copies_tree_and_excludes_runtime_files(tmp_path, fake_source):
    # Given : une copie de travail absente
    dest = tmp_path / "dest"
    # When : le déploiement est lancé
    done = run(fake_source, "--dest", str(dest), "--no-panel")
    # Then : l'arbre est copié, journaux et caches exclus
    assert done.returncode == 0
    assert (dest / "MediaSolution.jsx").is_file()
    assert (dest / "tools" / "outil.py").is_file()
    assert not (dest / "tools" / "export.log").exists()
    assert not (dest / "tools" / "__pycache__").exists()


def test_check_reports_drift_and_extras_without_touching_them(tmp_path, fake_source):
    # Given : une copie synchronisée
    dest = tmp_path / "dest"
    assert run(fake_source, "--dest", str(dest), "--no-panel").returncode == 0
    assert run(fake_source, "--dest", str(dest), "--no-panel", "--check").returncode == 0
    # When : un fichier source change et un fichier en trop apparaît dans la copie
    (fake_source / "tools" / "outil.py").write_text("print(2)\n", encoding="utf-8")
    (dest / "junk.tmp").write_text("x", encoding="utf-8")
    drift = run(fake_source, "--dest", str(dest), "--no-panel", "--check")
    # Then : les deux écarts sont signalés (sortie 1) sans rien modifier
    assert drift.returncode == 1
    assert "outil.py" in drift.stdout
    assert "junk.tmp" in drift.stdout
    assert (dest / "junk.tmp").exists()
    assert (dest / "tools" / "outil.py").read_text(encoding="utf-8") == "print(1)\n"


def test_prune_syncs_and_removes_extras_but_keeps_destination_logs(tmp_path, fake_source):
    # Given : une copie synchronisée, avec son propre journal, puis un fichier en trop
    dest = tmp_path / "dest"
    run(fake_source, "--dest", str(dest), "--no-panel")
    (dest / "tools" / "export.log").write_text("journal de la copie\n", encoding="utf-8")
    (dest / "junk.tmp").write_text("x", encoding="utf-8")
    (fake_source / "tools" / "outil.py").write_text("print(2)\n", encoding="utf-8")
    # When : la synchronisation est relancée avec --prune
    done = run(fake_source, "--dest", str(dest), "--no-panel", "--prune")
    # Then : le code est à jour, le fichier en trop supprimé, le journal de la copie préservé
    assert done.returncode == 0
    assert (dest / "tools" / "outil.py").read_text(encoding="utf-8") == "print(2)\n"
    assert not (dest / "junk.tmp").exists()
    assert (dest / "tools" / "export.log").read_text(encoding="utf-8") == "journal de la copie\n"


def test_panel_is_reinstalled_only_when_it_changes(tmp_path, fake_source):
    # Given : une copie synchronisée
    dest = tmp_path / "dest"
    run(fake_source, "--dest", str(dest), "--no-panel")
    # When : seul un outil change
    (fake_source / "tools" / "outil.py").write_text("print(3)\n", encoding="utf-8")
    other = run(fake_source, "--dest", str(dest))
    # Then : le panel n'est pas réinstallé
    assert "STUB_PANEL" not in other.stdout
    # When : le panel change
    (fake_source / "MediaSolution.jsx").write_text("// panel v2\n", encoding="utf-8")
    panel = run(fake_source, "--dest", str(dest))
    # Then : la copie déployée est réinstallée dans EffectCraft
    assert "STUB_PANEL" in panel.stdout


def test_deployed_copy_refuses_to_sync_itself(tmp_path, fake_source):
    # Given : la copie déployée (script lancé depuis la destination)
    dest = tmp_path / "dest"
    run(fake_source, "--dest", str(dest), "--no-panel")
    # When : on lance le script de la copie, avec elle-même comme destination
    done = run(dest, "--dest", str(dest))
    # Then : il refuse et renvoie le code d'usage
    assert done.returncode == 2
    assert "copie déployée" in done.stderr + done.stdout
