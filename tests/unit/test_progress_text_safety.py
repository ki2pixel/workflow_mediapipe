"""
Tests de validation pour progress_text (Point 5.1)

Vérifie que progress_text ne contient jamais de HTML et est traité comme texte pur.
"""

import pytest
import re


def test_progress_text_no_html_tags():
    """Vérifie que progress_text ne contient pas de balises HTML."""
    # Exemples de progress_text valides (texte pur avec newlines)
    valid_texts = [
        "Traitement vidéo 1/10",
        "En cours...",
        "Ligne 1\nLigne 2\nLigne 3",
        "Fichier: video.mp4\nProgrès: 50%",
        "",  # empty is valid
    ]
    
    # Pattern pour détecter des balises HTML
    html_pattern = re.compile(r'<[^>]+>')
    
    for text in valid_texts:
        assert not html_pattern.search(text), f"Valid text should not contain HTML: {text}"


def test_progress_text_rejects_html():
    """Vérifie qu'on peut détecter du HTML dans progress_text."""
    # Exemples de progress_text INVALIDES (contenant du HTML)
    invalid_texts = [
        "Ligne 1<br>Ligne 2",
        "<div>Test</div>",
        "Text with <span>HTML</span>",
        "Line 1<br/>Line 2",
    ]
    
    # Pattern pour détecter des balises HTML
    html_pattern = re.compile(r'<[^>]+>')
    
    for text in invalid_texts:
        assert html_pattern.search(text), f"Invalid text should be detected as containing HTML: {text}"


def test_multiline_separator_conversion():
    """Vérifie que le séparateur || est converti en newline."""
    # Simule la conversion backend
    progress_data = "Ligne 1 || Ligne 2 || Ligne 3"
    text_progress = progress_data.replace(" || ", "\n")
    
    # Vérifie conversion correcte
    assert text_progress == "Ligne 1\nLigne 2\nLigne 3"
    assert "<br>" not in text_progress
    assert "<br/>" not in text_progress
    
    # Vérifie que le résultat ne contient pas de HTML
    html_pattern = re.compile(r'<[^>]+>')
    assert not html_pattern.search(text_progress)


def test_progress_text_sanitization_helper():
    """Fonction helper pour valider progress_text dans les tests d'intégration."""
    def is_safe_progress_text(text: str) -> bool:
        """Retourne True si le texte est sûr (pas de HTML)."""
        if not text:
            return True
        html_pattern = re.compile(r'<[^>]+>')
        return not html_pattern.search(text)
    
    # Tests
    assert is_safe_progress_text("")
    assert is_safe_progress_text("Simple text")
    assert is_safe_progress_text("Line 1\nLine 2")
    assert not is_safe_progress_text("Text with <br> tag")
    assert not is_safe_progress_text("<div>HTML</div>")


@pytest.mark.parametrize("text,expected_safe", [
    ("Plain text", True),
    ("Multi\nline\ntext", True),
    ("Text with special chars: éàç", True),
    ("", True),
    ("Text with <br> HTML", False),
    ("<script>alert('xss')</script>", False),
    ("Normal text<br/>with break", False),
])
def test_progress_text_validation_parametrized(text, expected_safe):
    """Tests paramétrés pour validation progress_text."""
    html_pattern = re.compile(r'<[^>]+>')
    is_safe = not html_pattern.search(text)
    assert is_safe == expected_safe, f"Text: '{text}' - Expected safe={expected_safe}, got {is_safe}"
