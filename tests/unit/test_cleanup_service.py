import pytest
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from config.settings import config
from services.cleanup_service import CleanupService


@pytest.fixture
def mock_config(tmp_path):
    with patch("services.cleanup_service.config") as mock_conf:
        # Configuration des dossiers vitaux
        mock_conf.PROJECTS_DIR = tmp_path / "projets_extraits"
        mock_conf.PROJECTS_DIR.mkdir()
        
        mock_conf.ARCHIVES_DIR = tmp_path / "archives"
        mock_conf.ARCHIVES_DIR.mkdir()
        
        mock_conf.LOGS_DIR = tmp_path / "logs"
        mock_conf.LOGS_DIR.mkdir()
        
        yield mock_conf


def test_is_path_protected_global_dirs(mock_config, tmp_path):
    """Test que les dossiers globaux configurés sont protégés."""
    assert CleanupService.is_path_protected(mock_config.ARCHIVES_DIR) is True
    assert CleanupService.is_path_protected(mock_config.LOGS_DIR) is True


def test_is_path_protected_names(tmp_path):
    """Test que les dossiers par nom sont protégés."""
    archives_dir = tmp_path / "archives"
    archives_dir.mkdir()
    assert CleanupService.is_path_protected(archives_dir) is True
    
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    assert CleanupService.is_path_protected(docs_dir) is True


def test_is_path_protected_temp_names(tmp_path):
    """Test que les dossiers temporaires spécifiques (_temp_) sont protégés."""
    temp_dir = tmp_path / "_temp_extract_123"
    temp_dir.mkdir()
    assert CleanupService.is_path_protected(temp_dir) is True


def test_is_path_protected_normal_project(mock_config):
    """Test qu'un dossier de projet normal n'est pas protégé."""
    project_dir = mock_config.PROJECTS_DIR / "projet_normal_001"
    project_dir.mkdir()
    assert CleanupService.is_path_protected(project_dir) is False


def test_get_orphan_projects_identifies_old_directories(mock_config):
    """Teste que les répertoires anciens sont bien identifiés."""
    old_project = mock_config.PROJECTS_DIR / "old_projet"
    old_project.mkdir()
    
    # On simule une très ancienne date de modif (il y a 100 heures)
    old_time = time.time() - (100 * 3600)
    os.utime(old_project, (old_time, old_time))
    
    # Un projet récent
    new_project = mock_config.PROJECTS_DIR / "new_projet"
    new_project.mkdir()
    
    orphans = CleanupService.get_orphan_projects(threshold_hours=48)
    
    assert len(orphans) == 1
    assert orphans[0]["name"] == "old_projet"
    assert orphans[0]["age_hours"] >= 99


def test_cleanup_orphan_projects_removes_old_directories(mock_config):
    """Teste que le nettoyage supprime bien l'ancien dossier et laisse le récent."""
    old_project = mock_config.PROJECTS_DIR / "old_projet"
    old_project.mkdir()
    
    # Fichier bidon pour s'assurer qu'il supprime récursivement
    (old_project / "file.txt").touch()
    
    old_time = time.time() - (100 * 3600)
    os.utime(old_project / "file.txt", (old_time, old_time))
    os.utime(old_project, (old_time, old_time))
    
    # Projet récent
    new_project = mock_config.PROJECTS_DIR / "new_projet"
    new_project.mkdir()
    (new_project / "file.txt").touch()
    
    assert old_project.exists()
    assert new_project.exists()
    
    # Lancement du nettoyage
    results = CleanupService.cleanup_orphan_projects(threshold_hours=48, dry_run=False)
    
    # Vérifications
    assert len(results["cleaned_projects"]) == 1
    assert "old_projet" in results["cleaned_projects"]
    assert not old_project.exists()  # Doit être supprimé
    assert new_project.exists()      # Doit être conservé


def test_cleanup_orphan_projects_dry_run(mock_config):
    """Teste que le dry-run ne supprime rien."""
    old_project = mock_config.PROJECTS_DIR / "old_projet"
    old_project.mkdir()
    old_time = time.time() - (100 * 3600)
    os.utime(old_project, (old_time, old_time))
    
    assert old_project.exists()
    
    results = CleanupService.cleanup_orphan_projects(threshold_hours=48, dry_run=True)
    
    assert len(results["cleaned_projects"]) == 1
    assert "old_projet" in results["cleaned_projects"]
    assert old_project.exists()  # Ne doit PAS être supprimé en dry-run
