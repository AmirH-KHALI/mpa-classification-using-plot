# -*- coding: utf-8 -*-
"""BaseModelMovieClassification.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11kaoIfB33ZA9hVaOT8_fd1eKBvSnitZz

# Imports
"""

!pip install -q transformers datasets
!apt-get install rar

import pandas as pd
import numpy as np
import ast

import tensorflow as tf

from tensorflow.keras import layers
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.layers import TextVectorization
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer, EvalPrediction
from sklearn.metrics import f1_score, roc_auc_score, accuracy_score
import torch

from google.colab import drive, auth
# Mount Google Drive
drive.mount("/content/drive")

base_dir = './drive/MyDrive/University/00012-NLP/MovieClassification/'
# base_dir = './'

"""# Bert Sequence Generator"""

dataset = load_dataset('csv', data_files={'train': base_dir + 'data/cleaned/data.csv'})
dataset

dataset['train'][0]

labels = ['G', 'PG', 'PG-13', 'R']
id2label = {idx:label for idx, label in enumerate(labels)}
label2id = {label:idx for idx, label in enumerate(labels)}
labels

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

def preprocess_data(examples):   
    for i in range(len(examples['Normalized_Plot'])):
        examples['Normalized_Plot'][i] = ' '.join(ast.literal_eval(examples['Normalized_Plot'][i]))
    
    labels_batch_array = []
    # take a batch of texts
    text = examples["Normalized_Plot"]
    # encode them
    encoding = tokenizer(text, padding="max_length", truncation=True, max_length=128)
    rate = examples['MPA']
    for i in range(len(text)):
        labels_batch = {'G': False, 'PG': False, 'PG-13': False, 'R': False}
        labels_batch[rate[i]] = True
        labels_batch_array.append(labels_batch)

    # print(labels_batch_array)

    # create numpy array of shape (batch_size, num_labels)
    labels_matrix = np.zeros((len(text), len(labels)))
    # fill numpy array
    for i in range(len(text)):
        temp_dic = labels_batch_array[i]
        for idx, label in enumerate(labels):
            # print(temp_dic)
            labels_matrix[i, idx] = temp_dic[label]

    encoding["labels"] = labels_matrix.tolist()
    
    return encoding

encoded_dataset = dataset.map(preprocess_data, batched=True, remove_columns=dataset['train'].column_names)
encoded_dataset['train'][0].keys()

encoded_dataset.set_format("torch")

model = AutoModelForSequenceClassification.from_pretrained(
    "bert-base-uncased", 
    problem_type="multi_label_classification", 
    num_labels=len(labels),
    id2label=id2label,
    label2id=label2id
    )

args = TrainingArguments(
    f"bert-finetuned-sem_eval-english",
    evaluation_strategy = "epoch",
    save_strategy = "epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    num_train_epochs=5,
    weight_decay=0.01,
    load_best_model_at_end=True,
    metric_for_best_model='f1',
)

# source: https://jesusleal.io/2021/04/21/Longformer-multilabel-classification/
def multi_label_metrics(predictions, labels, threshold=0.5):
    # first, apply sigmoid on predictions which are of shape (batch_size, num_labels)
    sigmoid = torch.nn.Sigmoid()
    probs = sigmoid(torch.Tensor(predictions))
    # next, use threshold to turn them into integer predictions
    y_pred = np.zeros(probs.shape)
    y_pred[np.where(probs >= threshold)] = 1
    # finally, compute metrics
    y_true = labels
    f1_micro_average = f1_score(y_true=y_true, y_pred=y_pred, average='micro')
    roc_auc = roc_auc_score(y_true, y_pred, average = 'micro')
    accuracy = accuracy_score(y_true, y_pred)
    # return as dictionary
    metrics = {'f1': f1_micro_average,
               'roc_auc': roc_auc,
               'accuracy': accuracy}
    return metrics

def compute_metrics(p: EvalPrediction):
    preds = p.predictions[0] if isinstance(p.predictions, 
            tuple) else p.predictions
    result = multi_label_metrics(
        predictions=preds, 
        labels=p.label_ids)
    return result

trainer = Trainer(
    model,
    args,
    train_dataset=encoded_dataset["train"],
    eval_dataset=encoded_dataset["train"],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics
)

trainer.train()

pt_save_directory = base_dir + 'models/fine_tuned_bert'
tokenizer.save_pretrained(pt_save_directory)
model.save_pretrained(pt_save_directory)

zip_path = base_dir + 'models/fine_tuned_bert.zip'

!zip -r zip_path pt_save_directory