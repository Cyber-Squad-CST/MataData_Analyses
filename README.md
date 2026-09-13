# 🕵️‍♂️ Termux All-in-One DFIR Master Suite

ডিজিটাল ফরেনসিক ইভেস্টিগেশন, মেটাডাটা অ্যানালাইসিস, ফাইল স্পুফিং ডিটেকশন এবং ডিপ স্ট্রাকচার্ড এভিডেন্স এক্সট্রাকশনের জন্য একটি শক্তিশালী পাইথন ভিত্তিক DFIR (Digital Forensics and Incident Response) টুল।

---

## 🚀 বৈশিষ্ট্য (Key Features)

- **🖼️ EXIF & GPS metadata analysis:** ছবির সম্পূর্ণ ক্যামেরা সেন্সর তথ্য ও লাইভ Google Maps লোকেশন লিংক।
- **⚡ Flashlight & Hardware Decoders:** ক্যামেরার ফ্ল্যাশ স্টেট (Auto, Red-Eye, Compulsory) ও সেন্সর টাইপ (Front/Back) শনাক্তকরণ।
- **🧪 Magic Bytes File Spoofing Detector:** ফাইলের ফেক এক্সটেনশন ও স্পুফিং শনাক্তকরণ।
- **🎬 FFprobe Media Analyzer:** ভিডিও ও অডিও ফ্রেমরেট, রেজোলিউশন, ডিউরেশন ও বিটরেট তথ্য।
- **🕵️ Deep Forensic Tools:** হিডেন পে-লোড (Steganography Detection), IOC Extractor (IP, Email, URL) এবং EXIF থাম্বনেইল এক্সট্রাক্টর।
- **📄 Evidence Report Generator:** ফলাফল সহ সহজে পাঠযোগ্য `.txt` ও `.json` ফরম্যাটে অটোমেটিক ফরেনসিক রিপোর্ট সেভার।

---

## 🛠️ প্রয়োজনীয় ডিপেন্ডেন্সি ইন্সটলেশন (Installation)

Termux অথবা যেকোনো Linux সিস্টেমে টুলটি চালানোর আগে প্রয়োজনীয় সিস্টেম প্যাকেজ ও পাইথন মডিউলগুলো ইন্সটল করে নিন।

### ধাপ ১: সিস্টেম প্যাকেজসমূহ আপডেট ও ইন্সটল করুন
```bash
pkg update && pkg upgrade -y
pkg install python ffmpeg -y
