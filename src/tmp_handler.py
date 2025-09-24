import signal
import os
import sys
import tempfile

class TempFileHandler:
    def __init__(self):
        self.temp_path = None
        self.fd = None
        self._setup_signals()

    def _setup_signals(self):
        for s in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]:
            signal.signal(s, self._cleanup)
    
    def _cleanup(self, signum=None, frame=None):
        try:
            if self.fd:
                os.close(self.fd)
            
            if self.temp_path and os.path.exists(self.temp_path):
                os.unlink(self.temp_path)
        except Exception:
            pass
        if signum:
            sys.exit(1)

    def create(self, mode='w+b'):
        self.temp_path = tempfile.NamedTemporaryFile().name
        self.fd = os.open(self.temp_path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        os.unlink(self.temp_path)
        return self.fd
    
    def __enter__(self):
        return self.create()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()

    def __del__(self):
        self._cleanup()
        
