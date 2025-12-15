import logging
import time

logger = logging.getLogger(__name__)

class Tic():
    def __init__(self):
        self.st = time.time()
    def tic(self):
        self.st = time.time()
    
    def tac(self):
        self.et = time.time()
    
    def print_time(self, process_name: str):
        self.tac()
        logger.info("Process %s takes %.3fs.", process_name, self.et - self.st)