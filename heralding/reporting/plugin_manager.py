import os
import logging
import importlib

from heralding.reporting.base_logger import BaseLogger

logger = logging.getLogger(__name__)
moduleList = []

class PluginManager(BaseLogger):

    def __init__(self):
        super().__init__()
    path = os.path.dirname(os.path.realpath(__file__)) + '/plugins'
    logger.debug('Plugin manager started')
    if not os.path.exists(path):
        os.makedirs(path)
    for filename in os.listdir(path):
        if filename.endswith(".py"):
            moduleName = filename.split('.')[0]
            spec = importlib.util.spec_from_file_location(moduleName, os.path.dirname(os.path.realpath(__file__)) + '/plugins/' + filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.loaded()
            moduleList.append(module)

    def propagateData(self, data):
        for module in moduleList:
            register = module.register()
            register(data);

    #This function is called by heralding every time new login attempt is logged
    def handle_auth_log(self, data):
        if 'username' in data and 'password' in data:
            self.propagateData(data)


