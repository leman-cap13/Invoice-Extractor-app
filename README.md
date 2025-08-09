# Invoice-Extractor-app

The **Invoice Extractor App** is a web-based tool that lets you upload an invoice image and instantly extracts:
- 🆔 **Invoice Number**
- 📅 **Invoice Date**
- 💰 **Total Amount**

It runs entirely in your browser using a **Gradio interface** — no complex setup needed. Just upload your file, and the results appear in seconds.

---

## 🌟 Why Use This App?
Manually searching through invoices is slow and error-prone.  
This app:
- Automatically reads invoice text using **EasyOCR**  
- Detects key fields by matching invoice label patterns  
- Cleans and formats the extracted values  
- Works on scanned PDFs converted to images or photographed invoices  

---

## 🖥 How It Works (with Gradio)
1. **Upload Invoice** — Drag & drop or select an image from your computer.  
2. **OCR Processing** — The app converts the image to grayscale, applies adaptive thresholding, and uses **EasyOCR** to detect text.  
3. **Label Search** — The system looks for keywords like "Invoice No", "Date", "Total".  
4. **Value Extraction** — Finds and cleans the value near each label.  
5. **Display Results** — The extracted fields appear in **JSON format** directly in the browser.  


---

## 🚀 Quick Start
```bash
git clone https://github.com/leman-cap13/Invoice-Extractor-app.git
cd Invoice-Extractor-app
pip install -r requirements.txt
python main.py
