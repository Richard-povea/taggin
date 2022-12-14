import pandas as pd
import numpy as np
import json
import re
import os
import librosa

from typing import Tuple, Optional, Union

MAIN_TAXONOMY = ('blown','other_birds','dog','anthropophony_others','Theristicus_caudatus'
,'Milvago_chimango','alarm','Vanellus_chilensis','motor','siren'
,'rain_medium','Pleurodema_thaul','rain_drip','car_horn','rain_strong'
,'other_amphibians','Batrachyla_taeniata','Batrachyla_leptopus','whistle'
,'other_bird')
DATA_PATH = "taggin file/1039_modificado_v2.json"
DATA_AUDIO_FILES = '/home/vpoblete/Escritorio/audio_signals'

def filter_by_taxonomy(file: json, taxonomy: tuple) -> pd.DataFrame:
    """Read JSON file, filter and sort by file and taxonomy """
    
    df = pd.read_json(DATA_PATH, dtype={"path":str, 
                                        "file":str,
                                        "begining": float,
                                        "end": float,
                                        "taxonomy": str})
    #print(df['taxonomy'].unique())                                   
    df_filter = df.loc[df['taxonomy'].isin(taxonomy)]
    audios = df_filter['file'].unique()
    
    files_selected = df.set_index(['file', 'taxonomy']).loc[audios].copy(True)
    files_selected.sort_index(inplace=True)
    return files_selected

def create_dict_file(files_selected: pd.DataFrame) -> dict:
    """Create a dict file as:\n
        file name:\n
        --->Nº event:\n
        -------->taxonomy: str\n
        -------->beginning: float\n
        -------->end: float\n
        -------->length: float\n
    """
    time = dict()
    last_file = str()
    file_time = dict()
    event = 0
    for i, index in enumerate(files_selected.itertuples()):
        file, taxonomy = index[0]
        beginning = index[2]
        end = index[3]
        if (last_file != file) & (len(file_time) == 0):
            pass
        elif (last_file != file) & (len(file_time) >0):
            #.copy DON'T LOSE DATA!!!!
            time[last_file] = file_time.copy()
            file_time.clear()
            event = i
        last_file = file
        if taxonomy not in MAIN_TAXONOMY:
            continue
        file_time[f'{i+1-event} event'] = {'taxonomy':taxonomy, 'beginning':beginning, 'end':end, 'length': np.round(end-beginning,2)}
    time = {k: v for k, v in sorted(time.items(), key=lambda item: int(re.sub('[audio.wav]','',str(item[0]))))}
    return time

def write_json_file(data: dict, name: str, path: Optional[str]=None) -> None:
    """Export data as a JSON file"""
    if path:
        name = os.path.join(path, name)
    json_object = json.dumps(data, indent = 4)
    with open(name, "w") as outfile:
        outfile.write(json_object)
        
def validate_founded(founded: dict, data: pd.DataFrame)->dict:
    monophonic_events = list()
    for audio_file in founded.keys():
        df = pd.DataFrame(founded[audio_file]) 
        data2 = data.groupby(level=0).get_group(audio_file)
        #DEBUG
        
        # print(df)
        # print(data2)
        results =  find_time_data(df, data2)
        if results:
            #monophonic_events[audio_file] = results
            for result in results:
                result['file_name'] = audio_file
                monophonic_events.append(result)
    return monophonic_events
               
def find_time_data(df: pd.DataFrame, data: pd.DataFrame)->list[dict]:
    monophonic_events = list()
    for event in df.columns:            
        beginning, end, length = df[event].loc[['beginning','end', 'length']].values
        monophonic, _ = find_monophonic_event(data, beginning, end)
        # #DEBUG
        # print(event, monophonic, overlapping_tuple)
        if monophonic:
            monophonic_events.append({'taxonomy': df[event].loc['taxonomy'], 
                                      'start': beginning, 
                                      'end': end, 
                                      'length': length})
    return monophonic_events
        
def find_monophonic_event(data: pd.DataFrame, beginning: float, end: float) -> Tuple[Union[bool, Tuple[bool,bool,bool]]]:
    """Find overlapping of a event with others in the same file"""
    intermediate_event = len(data.loc[(data['beginning'] >= beginning) & (data['end'] <= end)]) == 1
    start_before = len(data.loc[(data['beginning'] < beginning) & (data['end'] >= beginning)]) == 0
    end_after = len(data.loc[(beginning < data['beginning']) & (data['beginning'] < end)]) == 0
    overall_event = len(data.loc[(data['beginning'] < beginning) & (data['end'] > end)]) == 0
    
    monophonic = intermediate_event & start_before & end_after & overall_event
    overlapping_tuple = (intermediate_event, start_before, end_after, overall_event)
    
    return monophonic, overlapping_tuple

def audio_lenght(audio_name: str) -> int:
    y, sr = librosa.load(os.path.join(DATA_AUDIO_FILES, audio_name), sr=None)
    return int(librosa.get_duration(y=y, sr=sr))

def find_bg_noise(data, audio_name: str, length: int):
    audio_len = np.arange(audio_lenght(audio_name))
    for start, end in zip(data['beginning'], data['end']):
        audio_len = np.setdiff1d(audio_len, np.arange(int(start), int(end)))
    return audio_len

def loop_data(data: pd.DataFrame):
    bg_noise_length = 10
    for audio_name in data.index.get_level_values(0):
        bg_noise = find_bg_noise(data, audio_name, bg_noise_length)
        if len(bg_noise) > bg_noise_length:
            print(bg_noise) 
        

def main()->None:
    data = filter_by_taxonomy(DATA_PATH, MAIN_TAXONOMY)
    loop_data(data)
    #time = create_dict_file(data)
    #write_json_file(time)
    #write_json_file(validate_founded(time, data), 'mp_ev_v3.json') 
    
    

if __name__ == '__main__':
    main()
