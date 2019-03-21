import pickle
import datetime as dt
from easydict import EasyDict
import yaml
import logging
import pathlib
from pathlib import Path

def load_config(config_file):
    with open(config_file, 'r') as fid:
        yaml_config = EasyDict(yaml.load(fid))
    return yaml_config

def now2str(format="%Y-%m-%d__%H-%M-%S"):
    # str_time = time.strftime("%Y-%b-%d-%H-%M-%S", time.localtime(time.time()))
    return dt.datetime.now().strftime(format)

def save_dump(dump_data, out_file):
    with open(out_file, 'wb') as fp:
        print('Writing to %s.' % out_file)
        #pickle.dump(dump_data, fp, pickle.HIGHEST_PROTOCOL)
        pickle.dump(dump_data, fp)

def load_dump(dump_file):
    with open(dump_file, 'rb') as fp:
        dump = pickle.load(fp)
        return dump

def init_logger(name='qf', to_console=True, log_file=None, level=logging.DEBUG,
                msg_fmt='[%(asctime)s]  %(message)s', time_fmt="%Y-%m-%d %H:%M:%S"):
    # create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # create formatter
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    formatter = logging.Formatter(msg_fmt, time_fmt)

    if logger.handlers != [] and isinstance(logger.handlers[0], logging.StreamHandler):
        logger.handlers.pop(0)
    # create console handler and set level to debug
    f = open("/tmp/debug", "w")          # example handler
    if to_console:
        f = None

    ch = logging.StreamHandler(f)
    ch.setLevel(level)
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    if log_file:
        fh = logging.FileHandler(log_file, mode='a', encoding=None, delay=False)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


class BaseDirs():
    def __init__(self, root_path='', data_path='input'):
        dir_list = []
        if root_path == '':
            self.root = Path().resolve().parent
        else:
            self.root = root_path

        self.data = self.root/data_path
        self.data.mkdir(exist_ok=True)

        self.models = self.root/'models'
        self.models.mkdir(exist_ok=True)

        self.runtime = self.root/'runtime'
        self.runtime.mkdir(exist_ok=True)

        self.log = self.root/'log'
        self.log.mkdir(exist_ok=True)

        self.tb_log = self.root/'tblog'
        self.tb_log.mkdir(exist_ok=True)

        self.tmp = self.root/'tmp'
        self.tmp.mkdir(exist_ok=True)

    def add_dir(self, base_dir, sub_dir):
        new_dir = setattr(base_dir, sub_dir, f'{base_dir}/{sub_dir}')
        new_dir.mkdir(exist_ok=True)

start_timestamp = now2str()

pdir = BaseDirs()
plog_file = pdir.log/f'{start_timestamp}.log'
plog = init_logger(log_file=plog_file)

#todo scoreboard
class Scoreboard():
    def __init__(self, sb_file, sb_len=11, sort='dec'):
        if sb_file.is_file():
            load_obj = load_dump(sb_file)
            self.__dict__.update(load_obj.__dict__)
        else:
            self.sb = []
            self.sb_len = sb_len
            self.sort = sort
            self.sb_file = sb_file

    def update(self, content:dict):
        self.sb.append(content)
        reverse = self.sort in 'decrease'
        self.sb.sort(key=lambda e: e['score'], reverse=reverse)

        #remove useless files
        if len(self.sb) > self.sb_len:
            del_file = self.sb[-1]['file']
            if del_file.is_file():
                del_file.unlink()
        self.sb = self.sb[:self.sb_len]

        save_dump(self, self.sb_file)

    def __len__(self):
        return len(self.sb)

    def __getitem__(self, idx):
        return self.sb[idx]

    def is_full(self):
        return len(self.sb) >= self.sb_len

