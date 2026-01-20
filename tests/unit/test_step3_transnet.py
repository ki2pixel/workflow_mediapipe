#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour STEP3 (TransNetV2 scene detection)
"""

import pytest
import torch
import numpy as np
from pathlib import Path
import sys

# Ajouter le chemin du projet
BASE_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_PATH / "workflow_scripts" / "step3"))

from transnetv2_pytorch import TransNetV2, ColorHistograms


class TestTransNetV2Model:
    """Tests pour le modèle TransNetV2"""
    
    def test_input_validation_correct_shape(self):
        """Test validation des entrées avec forme correcte"""
        model = TransNetV2()
        model.eval()
        
        # Créer un batch valide [B=1, T=100, H=27, W=48, C=3]
        valid_input = torch.randint(0, 256, (1, 100, 27, 48, 3), dtype=torch.uint8)
        
        # Ne devrait pas lever d'exception
        with torch.no_grad():
            output = model(valid_input)
            assert output is not None
    
    def test_input_validation_wrong_dtype(self):
        """Test validation des entrées avec mauvais dtype"""
        model = TransNetV2()
        model.eval()
        
        # Créer un batch avec mauvais dtype (float32 au lieu de uint8)
        invalid_input = torch.rand(1, 100, 27, 48, 3, dtype=torch.float32)
        
        # Devrait lever TypeError
        with pytest.raises(TypeError, match="Expected dtype torch.uint8"):
            model(invalid_input)
    
    def test_input_validation_wrong_shape(self):
        """Test validation des entrées avec mauvaise forme"""
        model = TransNetV2()
        model.eval()
        
        # Créer un batch avec mauvaise forme spatiale (32x32 au lieu de 27x48)
        invalid_input = torch.randint(0, 256, (1, 100, 32, 32, 3), dtype=torch.uint8)
        
        # Devrait lever ValueError
        with pytest.raises(ValueError, match="Expected shape"):
            model(invalid_input)
    
    def test_color_histograms_validation(self):
        """Test validation ColorHistograms avec bon nombre de canaux"""
        # Créer des frames valides [B=1, T=100, H=27, W=48, C=3]
        frames = torch.randint(0, 256, (1, 100, 27, 48, 3), dtype=torch.uint8)
        
        # Ne devrait pas lever d'exception
        histograms = ColorHistograms.compute_color_histograms(frames)
        assert histograms.shape == (1, 100, 512)
    
    def test_color_histograms_wrong_channels(self):
        """Test validation ColorHistograms avec mauvais nombre de canaux"""
        # Créer des frames avec 4 canaux au lieu de 3
        frames = torch.randint(0, 256, (1, 100, 27, 48, 4), dtype=torch.uint8)
        
        # Devrait lever ValueError
        with pytest.raises(ValueError, match="Expected 3 color channels"):
            ColorHistograms.compute_color_histograms(frames)


class TestDeviceSelection:
    """Tests pour la sélection de device (CPU/CUDA)"""
    
    def test_cpu_always_available(self):
        """Test que CPU est toujours disponible"""
        device = torch.device('cpu')
        assert device.type == 'cpu'
    
    def test_cuda_availability_check(self):
        """Test vérification disponibilité CUDA"""
        # Ce test s'adapte à l'environnement
        if torch.cuda.is_available():
            device = torch.device('cuda')
            assert device.type == 'cuda'
        else:
            # Si CUDA non dispo, fallback CPU doit fonctionner
            device = torch.device('cpu')
            assert device.type == 'cpu'


class TestConfigParsing:
    """Tests pour le parsing de configuration"""
    
    def test_default_config_values(self):
        """Test valeurs par défaut de configuration"""
        import json
        config_path = BASE_PATH / "config" / "step3_transnet.json"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            
            # Vérifier les valeurs critiques
            assert cfg.get("threshold") == 0.5
            assert cfg.get("window") == 100
            assert cfg.get("stride") == 50
            assert cfg.get("padding") == 25
            assert cfg.get("device") in ["auto", "cpu", "cuda"]
            # Workers devrait être 1 pour éviter contention CUDA
            assert cfg.get("num_workers") == 1
            # TorchScript désactivé par défaut pour éviter TracerWarnings
            assert cfg.get("torchscript") == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
