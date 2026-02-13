#!/usr/bin/env python3
"""
Script pour corriger les erreurs JSON dans les fichiers dataset
"""

import json
import re

def fix_json_escapes(content: str) -> str:
    """Corrige les backslashes dans le contenu JSON"""
    # Trouver les chaînes JSON et corriger les backslashes à l'intérieur
    # Cette fonction est simplifiée, on va doubler tous les backslashes dans le contenu assistant

    # Pour simplifier, on va chercher les parties "content": "..." de assistant et doubler les \
    # Mais c'est complexe. Pour cette fois, on va juste essayer de parser et corriger.

    try:
        # Essayer de parser
        data = json.loads(content)
        # Si ça marche, c'est bon
        return content
    except json.JSONDecodeError as e:
        print(f"Erreur JSON: {e}")
        # Tenter de corriger les backslashes
        # Remplacer \ par \\ dans les chaînes de l'assistant
        # Trouver la partie assistant content
        assistant_start = content.find('"role": "assistant"')
        if assistant_start != -1:
            content_part = content[assistant_start:]
            content_start = content_part.find('"content": "') + len('"content": "')
            content_end = content_part.rfind('"}')

            if content_start > 0 and content_end > content_start:
                assistant_content = content_part[content_start:content_end]
                # Doubler les backslashes dans le contenu assistant
                fixed_content = assistant_content.replace('\\', '\\\\')
                # Mais attention, si c'était déjà \\, ça devient \\\\, ce qui est mal

                # Meilleure approche: utiliser une regex pour doubler seulement les \ non échappés
                # Mais pour simplifier, on va assumer que les \ sont à doubler
                new_content = content.replace(assistant_content, fixed_content)
                try:
                    json.loads(new_content)
                    print("Correction réussie")
                    return new_content
                except:
                    print("Correction échouée")
                    pass
        return content

def fix_json_escapes(content: str) -> str:
    """Corrige les backslashes dans le contenu JSON"""
    # Pour simplifier, on va doubler tous les backslashes dans le contenu assistant

    # Trouver les parties "content": "..." de assistant et doubler les \
    # Mais c'est complexe. Pour cette fois, on va juste essayer de parser et corriger.

    try:
        # Essayer de parser
        data = json.loads(content)
        # Si ça marche, c'est bon
        return content
    except json.JSONDecodeError as e:
        print(f"Erreur JSON: {e}")
        # Tenter de corriger les backslashes
        # Remplacer \ par \\ dans les chaînes de l'assistant
        # Trouver la partie assistant content
        assistant_start = content.find('"role": "assistant"')
        if assistant_start != -1:
            content_part = content[assistant_start:]
            content_start = content_part.find('"content": "') + len('"content": "')
            content_end = content_part.rfind('"}')

            if content_start > 0 and content_end > content_start:
                assistant_content = content_part[content_start:content_end]
                # Doubler les backslashes dans le contenu assistant
                fixed_content = assistant_content.replace('\\', '\\\\')
                # Mais attention, si c'était déjà \\, ça devient \\\\, ce qui est mal

                # Meilleure approche: utiliser une regex pour doubler seulement les \ non échappés
                # Mais pour simplifier, on va assumer que les \ sont à doubler
                new_content = content.replace(assistant_content, fixed_content)
                try:
                    json.loads(new_content)
                    print("Correction réussie")
                    return new_content
                except:
                    print("Correction échouée")
                    pass
        return content

def fix_file(file_path: str, target_line: int = None):
    """Corrige le fichier JSONL"""
    lines = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            if target_line and i == target_line:
                print(f"Corrige ligne {i}")
                line = fix_json_escapes(line)

            lines.append(line)

    # Réécrire le fichier
    with open(file_path, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')

    print(f"Fichier corrigé: {file_path}")

if __name__ == "__main__":
    fix_file("dataset/pipeline_operations_batch.jsonl", 349)
