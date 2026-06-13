import os
import torch
from speechbrain.inference.speaker import EncoderClassifier

class EcapaWrapper(torch.nn.Module):
    def __init__(self, classifier):
        super().__init__()
        self.embedding_model = classifier.mods.embedding_model
        
    def forward(self, x):
        # x is (batch, 80, 300) to match the existing TFLite behavior
        # SpeechBrain expects (batch, time, features) -> (batch, 300, 80)
        x = x.transpose(1, 2)
        out = self.embedding_model(x)
        return out.squeeze(1) # Return (batch, 192)

def main():
    print("Loading SpeechBrain ECAPA-TDNN model...")
    classifier = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        run_opts={"device": "cpu"}
    )
    
    wrapper = EcapaWrapper(classifier)
    wrapper.eval()
    
    dummy_input = torch.randn(1, 80, 300)
    
    print("Exporting to ONNX with dynamic batch size...")
    onnx_path = "assets/ecapa_tdnn_speaker_float.onnx"
    os.makedirs("assets", exist_ok=True)
    
    torch.onnx.export(
        wrapper, 
        dummy_input, 
        onnx_path,
        export_params=True,
        opset_version=13,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    print(f"Successfully exported ONNX model to {onnx_path}")

if __name__ == "__main__":
    main()
