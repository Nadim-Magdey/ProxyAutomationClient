import threading
import asyncio
from mitmproxy.tools.dump import DumpMaster
from mitmproxy.options import Options
from pathlib import Path
from CertificatesEngine.CertificateManager import CertificateManager  # your class

class MitmproxyRunner(threading.Thread):
    def __init__(self, addon, host="127.0.0.1", port=8085, proxy_data=None):
        super().__init__(daemon=True)
        self.addon = addon
        self.host = host
        self.port = port
        self.proxy_data = proxy_data

        self.master = None
        self.loop = None
        self._stop_event = threading.Event()

        # Certificate manager
        self.cert_manager = CertificateManager()
        self.cert_manager.generate_ca() 

    def run(self):
        print("run method started")

        # Create a fresh event loop every time
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._run_master())
        except RuntimeError as e:
            if "Event loop stopped before Future completed" in str(e):
                print("Proxy loop stopped normally")
            else:
                raise
        finally:
            if not self.loop.is_closed():
                self.loop.close()
                print("Event loop closed")

    async def _run_master(self):
        # ... (Your setup code for opts and master is correct)
        print("_run_master method started")

        mode = None
        proxy_info = "No upstream proxy (direct connection)"
        print(f"proxy data in _run_master: {self.proxy_data}")

        if self.proxy_data:
            ip = self.proxy_data.get("ip", "")
            port = self.proxy_data.get("port", "")
            username = self.proxy_data.get("username")
            password = self.proxy_data.get("password")

            if ip and port:
                if username and password:
                    mode = f"upstream:http://{username}:{password}@{ip}:{port}"
                    proxy_info = f"Using upstream proxy with auth -> IP: {ip}, Port: {port}, Username: {username}"
                else:
                    mode = f"upstream:http://{ip}:{port}"
                    proxy_info = f"Using upstream proxy -> IP: {ip}, Port: {port}, No auth"

        print(f"[DEBUG] Proxy settings: {proxy_info}")

        # Use certificate paths
        cert_dir = Path(self.cert_manager.get_cert_dir()).resolve()

        opts_kwargs = dict(
                listen_host=self.host,
                listen_port=self.port,
                http2=True,
                confdir=str(cert_dir),
            )

        if mode:
            opts_kwargs["mode"] = [mode]

        opts = Options(**opts_kwargs)
        self.master = DumpMaster(opts, with_termlog=False, with_dumper=False)
        self.master.addons.add(self.addon)

        try:
            # This is the main blocking call for the proxy
            await self.master.run()
        except Exception as e:
            print(f"Proxy encountered error: {e}")
        finally:
            print("Master.run() has exited")

    def stop(self):
        """Safe stop called from the GUI/OperationService."""
        if self.master:
            try:
                # Check if loop is still running before scheduling shutdown
                if self.loop and self.loop.is_running():
                    self.loop.call_soon_threadsafe(self.master.shutdown)
                    print("Shutdown signal sent to Master")
                else:
                    # If loop is already dead, just trigger master shutdown manually
                    self.master.shutdown()
            except Exception as e:
                print(f"Error signaling master shutdown: {e}")

        # Don't join() here if you are calling this from the GUI thread 
        # and the thread is already finished.
        if self.is_alive():
            # Optional: wait a tiny bit for cleanup
            self.join(timeout=0.5)
