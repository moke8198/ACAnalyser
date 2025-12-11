import json
import math

def format_ms_to_time(ms):
    """Converts milliseconds (int/float) to a standard time string (m:ss.zzz)"""
    if ms is None or ms < 0:
        return "N/A"

    total_seconds = ms / 1000
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60

    # Ensure seconds are formatted to three decimal places
    return f"{minutes}:{seconds:06.3f}"

def analyze_ac_session(file_path):
    """
    Parses the Assetto Corsa session JSON and generates a lap analysis report.
    Returns: (list of report lines, summary_data)
    """
    summary_data = {
        'best_lap_ms': -1,
        'theoretical_ms': -1,
        'all_laps': [],          # RENAMED from 'valid_laps' to 'all_laps'
        'raw_data': None,
        'session_datetime': None # Included from previous update
    }

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            summary_data['raw_data'] = data
    except FileNotFoundError:
        return ["Error: File not found."], summary_data
    except json.JSONDecodeError:
        return ["Error: Invalid JSON file format."], summary_data
    except Exception as e:
        return [f"An unexpected error occurred: {e}"], summary_data

    # --- Extract Session Datetime from nested JSON ---
    session_datetime = None
    quick_drive_str = data.get('__quickDrive')
    if quick_drive_str:
        try:
            quick_drive_data = json.loads(quick_drive_str)
            session_datetime = quick_drive_data.get('dtv')
            if session_datetime:
                 session_datetime = session_datetime.split('+')[0].split('.')[0] 
        except json.JSONDecodeError:
            pass 
    # -----------------------------------------------------------

    # Basic data extraction
    track = data.get("track", "Unknown Track").replace("ks_", "").replace("-", " ")
    car = data.get("players", [{}])[0].get("car", "Unknown Car").replace("ks_", "").replace("_", " ")

    output = []
    output.append("=" * 50)
    output.append("   ASSETTO CORSA SESSION ANALYSIS   ")
    output.append("=" * 50)
    output.append(f"Track: {track.title()}")
    output.append(f"Car:   {car.title()}")
    
    if session_datetime:
        date_part = session_datetime.split('T')[0]
        time_part = session_datetime.split('T')[1]
        output.append(f"Date:  {date_part}")
        output.append(f"Time:  {time_part}")
    else:
        output.append("Time:  N/A (Could not extract session date/time)")

    output.append("-" * 50)

    # 1. Extract laps data
    laps_data = data.get('sessions', [{}])[0].get('laps', [])

    if not laps_data:
        return output + ["No lap data found for the session."], summary_data

    valid_laps_ms = []       # STILL only for calculations (best lap, average lap)
    sector_1_times = []      # STILL only for valid laps
    sector_2_times = []
    sector_3_times = []

    all_laps_for_db = []     # NEW: Collects ALL laps

    output.append("LAP HISTORY (Lap | Time | S1 | S2 | S3 | Valid)")
    for i, lap in enumerate(laps_data):
        lap_number = i + 1
        lap_time = lap.get("time", -1)
        sectors = lap.get("sectors", [-1, -1, -1])
        cuts = lap.get("cuts", 0)

        # A lap is considered VALID if time > 0 and no cuts occurred
        is_valid_flag = (lap_time > 0 and cuts == 0)

        time_str = format_ms_to_time(lap_time)

        # Handle S1, S2, S3 extraction safely
        s1_time = sectors[0] if len(sectors) > 0 and sectors[0] > 0 else -1
        s2_time = sectors[1] if len(sectors) > 1 and sectors[1] > 0 else -1
        s3_time = sectors[2] if len(sectors) > 2 and sectors[2] > 0 else -1

        s1_str = format_ms_to_time(s1_time)
        s2_str = format_ms_to_time(s2_time)
        s3_str = format_ms_to_time(s3_time)

        valid_status = "YES" if is_valid_flag else (f"CUTS ({cuts})" if cuts > 0 else "INVALID")
        output.append(f"{lap_number:3} | {time_str:10} | {s1_str:8} | {s2_str:8} | {s3_str:8} | {valid_status}")

        # --- Data Collection Logic ---
        # 1. Collect data for Summary Calculations (ONLY VALID LAPS)
        if is_valid_flag:
            valid_laps_ms.append(lap_time)
            if s1_time > 0: sector_1_times.append(s1_time)
            if s2_time > 0: sector_2_times.append(s2_time)
            if s3_time > 0: sector_3_times.append(s3_time)

        # 2. Prepare data for Database Insertion (ALL LAPS)
        all_laps_for_db.append({
            'lap_number': lap_number,
            'time': lap_time,
            'sectors': sectors,
            'cuts': cuts,
            'is_valid': 1 if is_valid_flag else 0 # Store 1 or 0
        })
        # --- End Data Collection Logic ---


    if not valid_laps_ms:
        return output + ["-" * 50, "No valid laps were recorded in the session."], summary_data

    # --- Summary Calculations (unchanged, still based on valid laps) ---
    output.append("-" * 50)
    # ... (rest of summary calculations are unchanged) ...
    total_laps = len(laps_data)
    valid_laps_count = len(valid_laps_ms)
    valid_rate = (valid_laps_count / total_laps) * 100
    best_lap_ms = min(valid_laps_ms)
    average_lap_ms = sum(valid_laps_ms) / len(valid_laps_ms)

    output.append(f"Total Valid Laps: {valid_laps_count}")
    output.append(f"Validity Rate:    {valid_rate:.1f}%")
    output.append(f"Best Lap Time:    {format_ms_to_time(best_lap_ms)}")
    output.append(f"Average Lap Time: {format_ms_to_time(int(average_lap_ms))}")

    # Theoretical Best (Supports 3 or 2 sectors)
    theoretical_best = -1
    if sector_1_times and sector_2_times and sector_3_times:
        best_s1, best_s2, best_s3 = min(sector_1_times), min(sector_2_times), min(sector_3_times)
        theoretical_best = best_s1 + best_s2 + best_s3
        output.append(f"Theoretical Best: {format_ms_to_time(theoretical_best)}")
        output.append(f"    (S1: {format_ms_to_time(best_s1)}, S2: {format_ms_to_time(best_s2)}, S3: {format_ms_to_time(best_s3)})")
    elif sector_1_times and sector_2_times:
        best_s1, best_s2 = min(sector_1_times), min(sector_2_times)
        theoretical_best = best_s1 + best_s2
        output.append(f"Theoretical Best: {format_ms_to_time(theoretical_best)}")
        output.append(f"    (S1: {format_ms_to_time(best_s1)}, S2: {format_ms_to_time(best_s2)})")
    else:
        output.append("Theoretical Best: N/A (Missing Sector Data)")

    output.append("-" * 50)

    # Populate summary data for the caller
    summary_data['best_lap_ms'] = best_lap_ms
    summary_data['theoretical_ms'] = theoretical_best
    summary_data['all_laps'] = all_laps_for_db # UPDATED KEY
    summary_data['session_datetime'] = session_datetime 

    return output, summary_data