import subprocess
import json
import re
import sys
import os

def run_rclone(cmd):
    result = subprocess.run(['rclone'] + cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        print(f"Error running rclone {' '.join(cmd)}: {result.stderr}")
    return result.stdout

def get_files(remote_path):
    print(f"Listing files in {remote_path}...")
    output = run_rclone(['lsjson', '-R', '--files-only', remote_path])
    if not output: return []
    try:
        return json.loads(output)
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        return []

def is_junk(name):
    lower = name.lower()
    junk_words = ['hello', 'world', 'test', 'readme', 'license', 'github', 'changelog', 'copy', 'unnamed', 'default', 'new_preset']
    if any(jw in lower for jw in junk_words) and len(name) < 20: # simple checks
        return True
    
    # Very short meaningless files
    if len(name.split('.')[0]) < 2:
        return True
        
    return False

def clean_pedal_name(name):
    pedals = [
        ('Klon', 'Klon Centaur'), ('Centaur', 'Klon Centaur'), ('TS9', 'Ibanez TS9'), 
        ('TS808', 'Ibanez TS808'), ('TubeScreamer', 'Tube Screamer'), ('Tube_Screamer', 'Tube Screamer'),
        ('SD1', 'Boss SD-1'), ('SD-1', 'Boss SD-1'), ('OD1', 'Boss OD-1'), ('OD-1', 'Boss OD-1'), 
        ('OCD', 'Fulltone OCD'), ('Plumes', 'EQD Plumes'), ('Rat', 'ProCo Rat'), ('ProCo', 'ProCo Rat'),
        ('BigMuff', 'Big Muff'), ('Big_Muff', 'Big Muff'), ('FuzzFace', 'Fuzz Face'), ('Fuzz_Face', 'Fuzz Face'), 
        ('ToneBender', 'Tone Bender'), ('Tone_Bender', 'Tone Bender'), ('MorningGlory', 'JHS Morning Glory'), 
        ('Morning_Glory', 'JHS Morning Glory'), ('BluesDriver', 'Boss BD-2'), ('Blues_Driver', 'Boss BD-2'), 
        ('BD2', 'Boss BD-2'), ('BD-2', 'Boss BD-2'), ('Timmy', 'Paul Cochrane Timmy'), 
        ('ZenDrive', 'Hermida Zendrive'), ('Zendrive', 'Hermida Zendrive'), ('KoT', 'Analogman KoT'), 
        ('KingOfTone', 'Analogman KoT'), ('King_Of_Tone', 'Analogman KoT'), ('PrinceOfTone', 'Analogman PoT'), 
        ('Prince_Of_Tone', 'Analogman PoT'), ('Duke_Of_Tone', 'MXR Duke of Tone'), ('Spark', 'TC Spark'), 
        ('Fortin33', 'Fortin 33'), ('Fortin_33', 'Fortin 33'), ('Fortin_Grind', 'Fortin Grind'),
        ('FortinGrind', 'Fortin Grind'), ('Maxon', 'Maxon OD'), ('OD808', 'Maxon OD808'), 
        ('HorizonDevices', 'Horizon Precision Drive'), ('PrecisionDrive', 'Horizon Precision Drive'), 
        ('MetalZone', 'Boss MT-2'), ('Metal_Zone', 'Boss MT-2'), ('MT2', 'Boss MT-2'),
        ('HM2', 'Boss HM-2'), ('HM-2', 'Boss HM-2'), ('HeavyMetal', 'Boss HM-2'), ('Heavy_Metal', 'Boss HM-2'), 
        ('DS1', 'Boss DS-1'), ('DS-1', 'Boss DS-1'), ('MXR', 'MXR Drive'), ('MXR_Drive', 'MXR Drive'), 
        ('Chase_Tone_Secret', 'Chase Tone Secret'), ('Echoplex', 'Echoplex Preamp')
    ]
    
    stem = name.rsplit('.', 1)[0]
    ext = '.' + name.rsplit('.', 1)[1] if '.' in name else ''
    
    clean = stem
    clean = re.sub(r'NAM_?Capture|Capture', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'George_B_|Helga_B_', '', clean)
    clean = re.sub(r'_+', ' ', clean).strip()
    
    found_pedals = []
    lower_name = clean.lower()
    for search_key, real_name in pedals:
        k = search_key.replace('_', '').lower()
        if k in lower_name.replace(' ', '').replace('-', ''):
            if real_name not in found_pedals:
                found_pedals.append(real_name)
            
    if found_pedals:
        clean = " + ".join(found_pedals)
        
    # Clean up name a bit more
    clean = clean.replace('  ', ' ')
    if len(clean) > 80:
        clean = clean[:80]
        
    return clean.strip() + ext
    
from concurrent.futures import ThreadPoolExecutor

def run_rename(cmd):
    run_rclone(cmd)

def process_pedals():
    remote = "gdrive2:IR_DEF_REPOSITORY/04_BOUTIQUE_PEDALS_NAM"
    files = get_files(remote)
    
    seen_names = {}
    commands = []
    
    for f in files:
        path = f['Path']
        name = f['Name']
        
        if is_junk(name):
            print(f"DELETING JUNK: {name}")
            commands.append(['delete', f"{remote}/{path}"])
            continue
            
        new_name = clean_pedal_name(name)
        new_name = new_name.replace(' ', '_').replace('+', 'and')
        
        # Avoid collisions
        base_new = new_name.rsplit('.', 1)[0] if '.' in new_name else new_name
        ext = '.' + new_name.rsplit('.', 1)[1] if '.' in new_name else ''
        
        c = 1
        final_new_name = new_name
        while final_new_name in seen_names or (final_new_name == name and final_new_name in seen_names):
            final_new_name = f"{base_new}_{c}{ext}"
            c += 1
            
        seen_names[final_new_name] = True
        
        if final_new_name != name:
            dir_path = path.rsplit('/', 1)[0] if '/' in path else ''
            new_path = f"{dir_path}/{final_new_name}" if dir_path else final_new_name
            print(f"RENAMING: {name} -> {final_new_name}")
            commands.append(['moveto', f"{remote}/{path}", f"{remote}/{new_path}"])

    print(f"Executing {len(commands)} operations for pedals...")
    with ThreadPoolExecutor(max_workers=10) as ex:
        ex.map(run_rename, commands)

def process_presets():
    remote = "gdrive2:IR_DEF_REPOSITORY/03_PRESETS_AND_MODELERS"
    files = get_files(remote)
    
    commands = []
    for f in files:
        path = f['Path']
        name = f['Name']
        lower = name.lower()
        
        if is_junk(name) or 'hello_world' in lower or 'helloworld' in lower or 'untitled' in lower or 'empty' in lower:
            print(f"DELETING PRESET JUNK: {name}")
            commands.append(['delete', f"{remote}/{path}"])
            continue
            
    print(f"Executing {len(commands)} operations for presets...")
    with ThreadPoolExecutor(max_workers=10) as ex:
        ex.map(run_rename, commands)

process_pedals()
process_presets()
print("DONE")
