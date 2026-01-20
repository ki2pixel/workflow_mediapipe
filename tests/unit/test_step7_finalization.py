#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import errno
import importlib.util
import logging
import subprocess
from pathlib import Path

import pytest


def _load_finalize_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / 'workflow_scripts' / 'step7' / 'finalize_and_copy.py'
    spec = importlib.util.spec_from_file_location('workflow_scripts.step7.finalize_and_copy', module_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestStep7FinalizationChmodFallback:
    def test_destination_supports_chmod_returns_false_on_eperm(self, tmp_path, monkeypatch):
        mod = _load_finalize_module()

        # Given: Preconditions
        def _raise_eperm(*_args, **_kwargs):
            raise OSError(errno.EPERM, 'Operation not permitted')

        monkeypatch.setattr(mod.os, 'chmod', _raise_eperm)

        dest_dir = tmp_path / 'dest'

        # When:  Operation to execute
        supports = mod._destination_supports_chmod(dest_dir)

        # Then:  Expected result/verification
        assert supports is False

    def test_copy_project_tree_falls_back_to_python_copy_when_chmod_unsupported(self, tmp_path, monkeypatch, caplog):
        mod = _load_finalize_module()

        # Given: Preconditions
        src = tmp_path / 'src_project'
        dst = tmp_path / 'dst_project'
        src.mkdir(parents=True)
        (src / 'hello.txt').write_text('hello', encoding='utf-8')

        # Given: Preconditions
        def _raise_eperm(*_args, **_kwargs):
            raise OSError(errno.EPERM, 'Operation not permitted')

        monkeypatch.setattr(mod.os, 'chmod', _raise_eperm)

        # Given: Preconditions
        def _fake_run(cmd, check=True, **_kwargs):
            if isinstance(cmd, list) and cmd:
                if cmd[0] == 'rsync':
                    raise FileNotFoundError('rsync not found')
                if cmd[0] == 'bash':
                    raise subprocess.CalledProcessError(returncode=1, cmd=cmd)
            raise AssertionError(f'Unexpected subprocess.run call: {cmd}')

        monkeypatch.setattr(mod.subprocess, 'run', _fake_run)

        caplog.set_level(logging.INFO)

        # When:  Operation to execute
        mod._copy_project_tree(src, dst)

        # Then:  Expected result/verification
        out_file = dst / 'hello.txt'
        assert out_file.exists()
        assert out_file.read_text(encoding='utf-8') == 'hello'

        # Then:  Expected result/verification
        assert 'Destination ne supporte pas chmod' in caplog.text
        assert 'cp --no-preserve a échoué' in caplog.text
