#!/usr/bin/env python3
"""
Script de test du modèle Mistral fine-tuné workflow_mediapipe
"""

import os
from mistralai import Mistral

def test_finetuned_model():
    """Test le modèle fine-tuné avec des questions techniques"""
    
    # Configuration
    api_key = os.getenv("MISTRAL_API_KEY", "EA1LN9ddFsblnq4xIaPHnjJpFjYwQWIM")
    model_id = "ft:mistral-small-latest:c55a2c39:20260212:3466ca39"
    
    client = Mistral(api_key=api_key)
    
    # Questions de test
    test_questions = [
        "Comment exécuter STEP5 avec MediaPipe CPU ?",
        "Quels sont les 5 environnements virtuels du projet ?",
        "Comment fonctionne le pattern Service Layer ?",
        "Quelle est la différence entre STEP6 et STEP7 ?",
        "Comment diagnostiquer une erreur STEP3 GPU memory ?"
    ]
    
    print("🧪 Test du modèle fine-tuné workflow_mediapipe")
    print(f"Modèle: {model_id}")
    print("=" * 60)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n📝 Question {i}: {question}")
        print("-" * 40)
        
        try:
            response = client.chat.complete(
                model=model_id,
                messages=[
                    {"role": "user", "content": question}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            answer = response.choices[0].message.content
            print(answer)
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        print("\n" + "=" * 60)
    
    print("\n✅ Test terminé")

if __name__ == "__main__":
    test_finetuned_model()
