from fastprogress import master_bar, progress_bar
from fastai.vision import *
from fastai.metrics import accuracy
from fastai.basic_data import *
from fastai.callbacks import *
import pandas as pd
from torch import optim
import re
import torch
from fastai import *
import torch.nn.functional as F
from torch.nn.parameter import Parameter
import torch.nn as nn
import pretrainedmodels
from collections import OrderedDict
import math
import argparse
import torchvision
import pprint
from utils import *
from models import *
from dataset import *



def run(config):
    name = f'{config.task.name}-{config.model.backbone}-{config.loss.name}'

    df = pd.read_csv(LABELS)
    change_new_whale(df, new_name=new_whale_id)
    df = filter_df(df, n_new_whale=-1, new_whale_id=new_whale_id)
    df_fname = df.set_index('Image')
    val_idxes = split_data_set(df, seed=1)

    #scoreboard = load_dump(pdir.models)
    scoreboard_file = pdir.models/f'scoreboard-{name}.pkl'
    sb_len = config.scoreboard.len
    scoreboard = Scoreboard(scoreboard_file, sb_len, sort='dec')

    batch_size = config.train.batch_size
    n_process = config.n_process
    data = (
        ImageList
            .from_df(df, TRAIN, cols=['Image'])
            #.filter_by_func(lambda fname: df_fname.at[Path(fname).name, 'Count'] > 3)
            .split_by_idx(val_idxes)
            #.split_by_valid_func(lambda path: path2fn(path) in val_fns)
            #.label_from_func(lambda path: fn2label[path2fn(path)])
            .label_from_df(cols='Id')
            .add_test(ImageList.from_folder(TEST))
            .transform(get_transforms(do_flip=False), size=SZ, resize_method=ResizeMethod.SQUISH)
            .databunch(bs=batch_size, num_workers=n_process, path=pdir.root)
            .normalize(imagenet_stats)
    )

    data.classes[-1] = 'new_whale'
    backbone = get_backbone(config)
    loss_fn = get_loss_fn(config)

    if config.model.head == 'MixHead':
        head = MixHead
    elif config.model.head == 'CosHead':
        head = CosHead

    learner = cnn_learner(data,
                          backbone,
                          loss_func=loss_fn,
                          custom_head=head(config),
                          init=None,
                          #path=pdir.root,
                          metrics=[accuracy, map5, mapkfast])

    if len(scoreboard) and scoreboard[0]['file'].is_file():
        model_file = scoreboard[0]['file'].name[:-4]
    elif (pdir.models/f'{name}-coarse.pth').is_file():
        model_file = f'{name}-coarse'
    else:
        print('something wrong')
        exit()

    model_file = 'densenet121-38'
    print(f'loading {model_file} ...')
    learner.load(model_file)

    test_ds = WhaleDataSet(config, mode='test')
    tst_dl = DataLoader(
        test_ds,
        batch_size=batch_size,
        shuffle=False,
        drop_last=False,
        pin_memory=True,
        num_workers=config.n_process
    )

    val_ds = WhaleDataSet(config, mode='val')
    val_dl = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        drop_last=False,
        pin_memory=True,
        num_workers=config.n_process
    )

    logits, y = predict_mixhead(learner.model, tst_dl)
    #acc = acc_with_unknown(logits, y)
    #top5 = mapk_with_unknown(logits, y)
    #print(acc, top5)
    #exit()

    tops = topk_mix(*logits)
    tops = tops.cpu().numpy()
    test_df = pd.read_csv(pdir.data/'sample_submission.csv')
    test_df = test_df.set_index('Image')
    with tqdm.tqdm(total=len(tops)) as pbar:
        for ri, class_idxes in enumerate(tops):
            fname = test_ds.test_list[ri].name
            row = ''
            for class_idx in class_idxes:
                row += test_ds.classes[class_idx]
                row += ' '
                pass
            test_df.at[fname, 'Id'] = row
            pbar.update(100)
    sub_file = f'../submission/{name}.csv'
    print(f'write to {sub_file}')
    test_df.to_csv(sub_file)


def parse_args():
    description = 'Train humpback whale identification'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-c', '--config', dest='config_file',
                        help='configuration filename',
                        default=None, type=str)
    return parser.parse_args()


def main():
    import warnings
    warnings.filterwarnings("ignore")

    print('Train humpback whale identification')
    args = parse_args()
    if args.config_file is None:
      raise Exception('no configuration file')

    config = load_config(args.config_file)
    pprint.PrettyPrinter(indent=2).pprint(config)
    #utils.prepare_train_directories(config)
    run(config)
    print('success!')


if __name__ == '__main__':
    main()


