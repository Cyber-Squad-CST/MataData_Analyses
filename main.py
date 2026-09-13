import os
import sys
import time
import stat
import json
import re
import hashlib
import subprocess
import zipfile
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

console = Console()

# Magic Bytes DB for File Spoofing Detection
MAGIC_BYTES = {
    b"\xFF\xD8\xFF": "🖼️ JPEG Image File",
    b"\x89PNG\r\n\x1a\n": "🖼️ PNG Image File",
    b"GIF87a": "🎞️ GIF Animation",
    b"GIF89a": "🎞️ GIF Animation",
    b"%PDF": "📄 PDF Document",
    b"PK\x03\x04": "📦 ZIP Archive / APK / JAR / DOCX",
    b"Rar!\x1a\x07": "📦 RAR Archive",
    b"\x7fELF": "⚙️ Linux/Android Executable (ELF)",
    b"MZ": "🖥️ Windows Executable (EXE/DLL)",
    b"\x1f\x8b": "🗜️ GZIP Compressed Archive",
    b"\x4f\x67\x67\x53": "🎵 OGG Audio/Video",
    b"RIFF": "🎬 WAV / AVI / WEBP Media Container"
}

def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")

def print_banner():
    banner_art = """
[bold red]██████╗ ███████╗██╗██████╗ [/bold red]  [bold cyan]███████╗██╗  ██╗████████╗██████╗  █████╗  ██████╗████████╗[/bold cyan]
[bold red]██║  ██║██╔════╝██║██╔══██╗[/bold red]  [bold cyan]██╔════╝╚██╗██╔╝╚══██╔══╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝[/bold cyan]
[bold red]██║  ██║█████╗  ██║██████╔╝[/bold red]  [bold cyan]█████╗   ╚███╔╝    ██║   ██████╔╝███████║██║        ██║   [/bold cyan]
[bold red]██║  ██║██╔══╝  ██║██╔══██╗[/bold red]  [bold cyan]██╔══╝   ██╔██╗    ██║   ██╔══██╗██╔══██║██║        ██║   [/bold cyan]
[bold red]██████╔╝██║     ██║██║  ██║[/bold red]  [bold cyan]███████╗██╔╝ ██╗   ██║   ██║  ██║██║  ██║╚██████╗   ██║   [/bold cyan]
[bold red]╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝[/bold red]  [bold cyan]╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝   ╚═╝   [/bold cyan]
[bold yellow] 🕵️‍♂️🔥 TERMUX ALL-IN-ONE DFIR FORENSIC & METADATA MASTER SUITE 🔥🕵️‍♂️ [/bold yellow]
    """
    console.print(Panel(banner_art, border_style="bold red", padding=(0, 2)))

def get_readable_size(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0

def calculate_hashes(file_path):
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha1.hexdigest(), sha256.hexdigest()

def verify_file_signature(file_path):
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)
        for magic, file_type in MAGIC_BYTES.items():
            if header.startswith(magic):
                return file_type, header[:8].hex().upper()
        return "❓ Unknown Raw Signature", header[:8].hex().upper()
    except Exception:
        return "❌ Error Reading Signature", "N/A"

def format_duration(seconds_float):
    try:
        total_seconds = int(float(seconds_float))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d} ({seconds_float:.2f} sec)"
        return f"{minutes:02d}:{secs:02d} ({seconds_float:.2f} sec)"
    except Exception:
        return str(seconds_float)

def decode_flash_details(value):
    flash_codes = {
        0: "⚡ OFF - Flash did not fire",
        1: "⚡ ON - Flash fired",
        5: "⚡ ON - Flash fired, strobe return light not detected",
        7: "⚡ ON - Flash fired, strobe return light detected",
        9: "⚡ ON - Flash fired, compulsory mode",
        13: "⚡ ON - Flash fired, compulsory mode, return light not detected",
        15: "⚡ ON - Flash fired, compulsory mode, return light detected",
        16: "⚡ OFF - Flash did not fire, compulsory mode",
        24: "⚡ OFF - Flash did not fire, Auto mode",
        25: "⚡ ON - Flash fired, Auto mode",
        29: "⚡ ON - Flash fired, Auto mode, return light not detected",
        31: "⚡ ON - Flash fired, Auto mode, return light detected",
        32: "⚡ Flash function unavailable",
        65: "⚡ ON - Flash fired, Red-eye reduction mode",
        73: "⚡ ON - Flash fired, Compulsory mode, Red-eye reduction",
        89: "⚡ ON - Flash fired, Auto mode, Red-eye reduction"
    }
    return flash_codes.get(value, f"Raw Flash Code: {value}")

def detect_camera_type(focal_length, lens_model):
    lens_str = str(lens_model).lower() if lens_model else ""
    if "front" in lens_str or "selfie" in lens_str:
        return "🤳 Front / Selfie Camera"
    elif "back" in lens_str or "rear" in lens_str:
        return "📸 Back / Rear Camera"
        
    if focal_length:
        try:
            fl = float(focal_length)
            if fl < 3.0:
                return "📸 Back Camera (Ultra-Wide Sensor)"
            elif 3.0 <= fl <= 6.5:
                return "📸 Back Camera (Main Primary Sensor)"
            elif fl > 6.5:
                return "🔭 Back Camera (Telephoto Zoom Lens)"
        except Exception:
            pass
            
    return "📷 Standard Camera Sensor"

def convert_to_degrees(value):
    d, m, s = float(value[0]), float(value[1]), float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def extract_gps_info(exif_data):
    gps_info = {}
    for tag_id, value in exif_data.items():
        tag_name = TAGS.get(tag_id, tag_id)
        if tag_name == "GPSInfo":
            for key in value:
                sub_tag = GPSTAGS.get(key, key)
                gps_info[sub_tag] = value[key]
                
    if gps_info:
        try:
            gps_latitude = gps_info.get("GPSLatitude")
            gps_latitude_ref = gps_info.get("GPSLatitudeRef")
            gps_longitude = gps_info.get("GPSLongitude")
            gps_longitude_ref = gps_info.get("GPSLongitudeRef")

            if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
                lat = convert_to_degrees(gps_latitude)
                if gps_latitude_ref != "N": lat = -lat
                lon = convert_to_degrees(gps_longitude)
                if gps_longitude_ref != "E": lon = -lon

                return lat, lon, f"https://www.google.com/maps?q={lat},{lon}"
        except Exception:
            pass
    return None, None, None

def scan_strings_and_ioc(file_path):
    try:
        with open(file_path, 'rb') as f:
            content = f.read(200000)
        printable = content.decode('ascii', errors='ignore')
        
        emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', printable)))
        ips = list(set(re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', printable)))
        urls = list(set(re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', printable)))
        
        ioc_summary = []
        if ips: ioc_summary.append(f"🌐 IPs: {', '.join(ips[:2])}")
        if emails: ioc_summary.append(f"📧 Emails: {', '.join(emails[:2])}")
        if urls: ioc_summary.append(f"🔗 URLs: {', '.join(urls[:2])}")
        
        return " | ".join(ioc_summary) if ioc_summary else "🟢 No prominent IOCs found in header"
    except Exception:
        return "⚠️ IOC Extraction Error"

def check_steganography_eof(file_path, file_ext):
    try:
        if file_ext in [".JPG", ".JPEG"]:
            with open(file_path, 'rb') as f:
                content = f.read()
                eof_pos = content.rfind(b'\xff\xd9')
                if eof_pos != -1 and (len(content) - eof_pos - 2) > 100:
                    hidden_bytes = len(content) - eof_pos - 2
                    return f"🚨 SUSPICIOUS! {hidden_bytes} Bytes payload hidden after EOF tag!"
        return "🛡️ Clean (No extra payload hidden after file EOF)"
    except Exception:
        return "⚠️ Stego Test Error"

def extract_thumbnail(clean_path, base_name):
    try:
        with open(clean_path, 'rb') as f:
            exif_raw = f.read()
            start = exif_raw.find(b'\xff\xd8', 2)
            end = exif_raw.find(b'\xff\xd9', start)
            if start != -1 and end != -1:
                thumb_dir = "extracted_thumbnails"
                os.makedirs(thumb_dir, exist_ok=True)
                thumb_path = os.path.join(thumb_dir, f"Thumb_{base_name}.jpg")
                with open(thumb_path, 'wb') as thumb_file:
                    thumb_file.write(exif_raw[start:end+2])
                return f"📸 EXIF Thumbnail Saved -> {thumb_path}"
    except Exception:
        pass
    return "🖼️ No Embedded EXIF Thumbnail"

def save_evidence_report(file_name, report_data):
    output_dir = "forensic_reports"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(file_name)[0]

    console.print("\n[bold yellow]📄 সেভ ফরম্যাট নির্ধারণ করুন:[/bold yellow]")
    console.print("[1] 📝 Text Evidence Report (.txt)")
    console.print("[2] 📊 JSON Artifact Data (.json)")
    console.print("[3] ⚡ উভয় ফরম্যাটে সেভ করুন (TXT + JSON)")
    console.print("[4] ❌ সেভ করার প্রয়োজন নেই")

    choice = Prompt.ask("আপনার অপশন নির্বাচন করুন", choices=["1", "2", "3", "4"], default="1")
    if choice == "4": return

    if choice in ["1", "3"]:
        txt_path = os.path.join(output_dir, f"DFIR_Report_{base_name}_{timestamp}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("="*70 + "\n")
            f.write(f"           DIGITAL FORENSIC EVIDENCE REPORT\n")
            f.write(f"  Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*70 + "\n\n")
            for k, v in report_data.items():
                f.write(f"{k:<38} : {v}\n")
            f.write("\n" + "="*70 + "\n")
        console.print(f"[bold green]✅ Text রিপোর্ট সফলভাবে সেভ হয়েছে:[/bold green] [cyan]{txt_path}[/cyan]")

    if choice in ["2", "3"]:
        json_path = os.path.join(output_dir, f"DFIR_Report_{base_name}_{timestamp}.json")
        json_output = {
            "forensic_metadata": {
                "generated_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "artifacts": report_data
            }
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_output, f, indent=4, ensure_ascii=False)
        console.print(f"[bold green]✅ JSON রিপোর্ট সফলভাবে সেভ হয়েছে:[/bold green] [cyan]{json_path}[/cyan]")

def analyze_forensic_artifacts(file_path):
    clean_path = file_path.strip('"').strip("'").strip()
    if not os.path.exists(clean_path):
        console.print("\n[bold red]❌ ত্রুটি! ফাইলটি পাওয়া যায়নি। ফাইল পাথ পুনরায় চেক করুন।[/bold red]\n")
        return

    file_name = os.path.basename(clean_path)
    base_name = os.path.splitext(file_name)[0]
    file_ext = os.path.splitext(file_name)[1].upper()

    table = Table(title=f"\n🛡️ [bold red]DFIR Forensic Artifact Breakdown:[/bold red] [bold yellow]{file_name}[/bold yellow]", show_lines=True)
    table.add_column("🎨 Artifact / Attribute", style="bold cyan", justify="left")
    table.add_column("🔍 Forensic Evidence Details", style="bold white", justify="left")

    report_data = {}
    stats = os.stat(clean_path)

    # --- 1. SYSTEM & FILE SYSTEM ARTIFACTS ---
    report_data["📄 File Name"] = file_name
    report_data["🏷️ Extension Claimed"] = file_ext if file_ext else "No Extension"
    report_data["📁 Absolute File Path"] = os.path.abspath(clean_path)
    report_data["💾 File Size"] = f"{stats.st_size} Bytes ({get_readable_size(stats.st_size)})"
    report_data["🔒 Permissions Mode"] = stat.filemode(stats.st_mode)
    report_data["📌 Inode ID"] = str(stats.st_ino)
    report_data["👤 Owner UID / GID"] = f"UID: {stats.st_uid} | GID: {stats.st_gid}"
    report_data["🔗 Hard Links Count"] = str(stats.st_nlink)
    report_data["💽 Device ID"] = str(stats.st_dev)
    
    # MAC Timestamps
    report_data["🕒 Creation Time (BTime/CTime)"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_ctime))
    report_data["👁️ Last Access Time (ATime)"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_atime))
    report_data["✏️ Last Modified Time (MTime)"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_mtime))

    # --- 2. CRYPTOGRAPHIC HASHING ---
    md5, sha1, sha256 = calculate_hashes(clean_path)
    report_data["🔐 MD5 Hash"] = md5
    report_data["🔐 SHA-1 Hash"] = sha1
    report_data["🔐 SHA-256 Hash"] = sha256

    # --- 3. MAGIC BYTES & FILE SPOOFING DETECTOR ---
    detected_type, hex_header = verify_file_signature(clean_path)
    report_data["🧪 Magic Bytes Header (Hex)"] = hex_header
    
    is_spoofed = False
    if file_ext == ".JPG" and "JPEG" not in detected_type and "Unknown" not in detected_type:
        is_spoofed = True
    elif file_ext == ".PNG" and "PNG" not in detected_type and "Unknown" not in detected_type:
        is_spoofed = True
    elif file_ext == ".PDF" and "PDF" not in detected_type and "Unknown" not in detected_type:
        is_spoofed = True

    if is_spoofed:
        report_data["⚠️ Spoofing Warning"] = f"MALICIOUS/SPOOFED FILE DETECTED! Claimed: {file_ext}, Header: {detected_type}"
    else:
        report_data["🔍 Verified Header Type"] = detected_type

    # --- 4. DEEP FORENSIC ADDITIONS (IOC, STENOGRAPHY, THUMBNAIL) ---
    report_data["🕵️ Strings/IOC Scanner"] = scan_strings_and_ioc(clean_path)
    report_data["🛡️ Steganography Payload Check"] = check_steganography_eof(clean_path, file_ext)

    if file_ext in [".JPG", ".JPEG"]:
        report_data["🖼️ EXIF Thumbnail Extraction"] = extract_thumbnail(clean_path, base_name)

    # --- 5. MEDIA STREAM ANALYSIS (FFPROBE) ---
    video_extensions = [".MP4", ".MKV", ".AVI", ".MOV", ".FLV", ".WEBM", ".3GP", ".M4V", ".WMV", ".MP3", ".WAV", ".FLAC"]
    if file_ext in video_extensions:
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', clean_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            data = json.loads(result.stdout)
            
            format_info = data.get('format', {})
            streams = data.get('streams', [])
            
            if format_info.get('duration'):
                report_data["⏱️ Playback Duration"] = format_duration(float(format_info['duration']))
            if format_info.get('bit_rate'):
                report_data["📊 Overall Bitrate"] = f"{int(format_info['bit_rate']) // 1000} kbps"
            if format_info.get('format_long_name'):
                report_data["🎬 Container Format"] = str(format_info['format_long_name'])

            for i, stream in enumerate(streams):
                codec_type = stream.get('codec_type', '').upper()
                codec_name = stream.get('codec_name', '').upper()
                
                if codec_type == 'VIDEO':
                    if stream.get('width') and stream.get('height'):
                        report_data[f"📺 Video Stream #{i} Resolution"] = f"{stream['width']} x {stream['height']} Pixels"
                    report_data[f"📼 Video Codec #{i}"] = codec_name
                    if stream.get('r_frame_rate') and '/' in stream['r_frame_rate']:
                        num, den = map(int, stream['r_frame_rate'].split('/'))
                        if den > 0:
                            report_data[f"🎞️ Frame Rate #{i}"] = f"{(num / den):.2f} fps"
                    if stream.get('bit_rate'):
                        report_data[f"⚡ Video Bitrate #{i}"] = f"{int(stream['bit_rate']) // 1000} kbps"

                elif codec_type == 'AUDIO':
                    report_data[f"🎵 Audio Codec #{i}"] = codec_name
                    if stream.get('sample_rate'):
                        report_data[f"🎼 Audio Sample Rate #{i}"] = f"{int(stream['sample_rate'])} Hz"
                    if stream.get('channels'):
                        report_data[f"🔊 Audio Channels #{i}"] = f"{stream['channels']} Channel(s)"
        except Exception as e:
            report_data["🎥 FFprobe Stream Error"] = str(e)

    # --- 6. EXIF, GPS & CAMERA SENSOR ANALYSIS ---
    if file_ext in [".JPG", ".JPEG", ".PNG", ".TIFF", ".WEBP"]:
        try:
            with Image.open(clean_path) as img:
                report_data["📐 Image Dimensions"] = f"{img.width} x {img.height} Pixels"
                report_data["🎨 Color Mode"] = str(img.mode)
                
                exif_data = img._getexif()
                if exif_data:
                    lat, lon, maps_url = extract_gps_info(exif_data)
                    if maps_url:
                        report_data["📍 GPS Coordinates"] = f"{lat:.6f}, {lon:.6f}"
                        report_data["🗺️ Google Maps Location"] = maps_url
                    else:
                        report_data["📍 GPS Status"] = "No GPS geolocation metadata"

                    focal_len = None
                    lens_model = None
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if tag_name == "FocalLength": focal_len = value
                        elif tag_name == "LensModel": lens_model = value

                    report_data["📷 Camera Hardware Unit"] = detect_camera_type(focal_len, lens_model)

                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        
                        if tag_name == "Make":
                            report_data["📱 Device Manufacturer"] = str(value)
                        elif tag_name == "Model":
                            report_data["📱 Device Model Name"] = str(value)
                        elif tag_name == "Software":
                            report_data["⚙️ Software / Kernel Version"] = str(value)
                        elif tag_name == "DateTimeOriginal":
                            report_data["🕒 Photo Capture Timestamp"] = str(value)
                        elif tag_name == "Flash":
                            report_data["⚡ Flashlight State"] = decode_flash_details(value)
                        elif tag_name == "FocalLength":
                            report_data["🔍 Focal Length"] = f"{value} mm"
                        elif tag_name == "ISOSpeedRatings":
                            report_data["💡 ISO Sensitivity"] = str(value)
                        elif tag_name == "ExposureTime":
                            report_data["⏱️ Shutter Speed / Exposure Time"] = f"{value} sec"
                        elif tag_name == "FNumber":
                            report_data["📷 Aperture F-Stop"] = f"f/{value}"
                        elif tag_name == "LensModel":
                            report_data["🔍 Lens Model String"] = str(value)
                        elif tag_name == "ImageUniqueID" or tag_name == "BodySerialNumber":
                            report_data["🔢 Device Serial / Unique ID"] = str(value)
                        elif tag_name == "ShutterCount":
                            report_data["📸 Shutter Press Count"] = str(value)
                        elif tag_name != "GPSInfo":
                            if isinstance(value, bytes) and len(value) > 40:
                                value = "<Binary Payload Stream>"
                            report_data[f"EXIF: {tag_name}"] = str(value)
                else:
                    report_data["EXIF Status"] = "No EXIF metadata found"
        except Exception:
            report_data["Image EXIF Status"] = "Failed to parse EXIF payload"

    # Terminal Output Table Rendering
    for key, val in report_data.items():
        if "MALICIOUS" in str(val) or "SPOOFED" in str(val) or "SUSPICIOUS" in str(val):
            table.add_row(key, f"[bold red]{val}[/bold red]")
        elif "http" in str(val):
            table.add_row(key, f"[bold underline yellow]{val}[/bold underline yellow]")
        else:
            table.add_row(key, str(val))

    console.print(table)
    console.print("\n[bold green]✅ ফরেনসিক স্ক্যান সম্পূর্ণ সফলভাবে শেষ হয়েছে![/bold green]")

    # Save evidence report
    save_evidence_report(file_name, report_data)

def main():
    while True:
        clear_screen()
        print_banner()

        user_input = Prompt.ask("[bold yellow]📂 এভিডেন্স ফাইল/ইমেজ/ভিডিওর পাথ দিন (বন্ধ করতে 'q' লিখুন)[/bold yellow]")
        
        if user_input.lower() in ['q', 'exit', 'quit']:
            console.print("\n[bold cyan]DFIR Master Analyzer বন্ধ করা হয়েছে। ধন্যবাদ![/bold cyan]\n")
            break

        analyze_forensic_artifacts(user_input)
        
        console.print("\n" + "─"*70)
        Prompt.ask("[bold green]পরবর্তী ফাইল ইনভেস্টিগেট করতে [Enter] চাপুন...[/bold green]")

if __name__ == "__main__":
    main()
