# from .globals import set_CERTIFICATE_PATH, get_CERTIFICATE_PATH, check_certificate_path , set_host, set_port, get_host, get_port

# class ConfigManager:
#     def __init__(self):
#         pass
#     @staticmethod
#     def clear_certificates()->bool:
#         path = get_CERTIFICATE_PATH()
#         if path:
#             import shutil
#             shutil.rmtree(path)
#         set_CERTIFICATE_PATH(None)

#     @staticmethod
#     def flush_socket():
#         """set port and host to null"""
#         set_host(None)
#         set_port(None)
#     @staticmethod
#     def clear_all():
#         ConfigManager.clear_certificates()
#         ConfigManager.flush_socket()