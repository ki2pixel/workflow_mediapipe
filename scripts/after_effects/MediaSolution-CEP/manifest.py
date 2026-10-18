import os
import PyShiftAE as ae

def main():
    manifest = ae.Manifest()
    manifest.name = "MediaSolution-CEP"
    manifest.version = "12.0.0"
    manifest.description = "Media Solution CEPy Extension Bridge"
    manifest.author = "Workflow MediaPipe"
    manifest.dependencies = ["PyShiftAE"]
    manifest.entry = os.path.dirname(os.path.realpath(__file__)) + "/entry.py"
    return manifest

manifest = main()
dependencies = manifest.dependencies
