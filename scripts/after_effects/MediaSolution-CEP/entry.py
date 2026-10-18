import sys
import os
import json

# Add scripts directory, PyShiftBridge, and py_aep to sys.path
# Recherche portable : on ajoute Documents/Scripts (et sous-dossiers connus)
# au sys.path s'ils existent, sans chemin machine codé en dur.
documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
scripts_dir = os.path.join(documents_dir, "Scripts")
bridge_dir = os.path.join(scripts_dir, "PyShiftBridge")
for p in [scripts_dir, bridge_dir]:
    if p not in sys.path and os.path.isdir(p):
        sys.path.insert(0, p)

try:
    from PyShiftBridge import bridge_daemon
except ImportError:
    bridge_daemon = None

def ping(param1=None):
    """CEPy pipe ping handler."""
    return json.dumps({
        "ok": True,
        "result": {
            "status": "ok",
            "transport": "internal",
            "version": "1.0.1"
        },
        "error": None
    })

def mediasolution_apply_cuts_active_layer(param1):
    """CEPy pipe handler for apply cuts."""
    try:
        args = json.loads(param1) if isinstance(param1, str) else param1
        if bridge_daemon is None:
            raise RuntimeError("PyShiftBridge.bridge_daemon introuvable : vérifiez Documents/Scripts/PyShiftBridge")
        result = bridge_daemon.handle_entrypoint("mediasolution_apply_cuts_active_layer", args)
        return json.dumps({"ok": True, "result": result, "error": None})
    except Exception as e:
        import traceback
        return json.dumps({
            "ok": False,
            "result": None,
            "error": f"{e}\n{traceback.format_exc()}"
        })
