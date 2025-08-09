import easyocr
import cv2
import numpy as np
import re
from dateutil import parser

class InvoiceExtractor:
    def __init__(self, gpu=False):
        self.reader = easyocr.Reader(['en'], gpu=gpu)
        self.invoice_number_labels = [
            "invoice #", "invoice no", "invoice number", "inv no", "inv#", "bill no", "bill number"
        ]
        self.date_labels = [
            "invoice date", "date", "due date", "p.o.#", "date of issue", "bill date"
        ]
        self.total_labels = [
            "total", "total amount", "amount due", "grand total", "balance due", "total due"
        ]

    @staticmethod
    def preprocess_image(pil_image):
        img = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10
        )
        return processed

    @staticmethod
    def polygon_to_bbox(polygon):
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        return (min(xs), min(ys), max(xs), max(ys))

    @staticmethod
    def clean_text(text):
        text = text.replace("＃", "#").replace("＃", "#")
        return re.sub(r'[\s\.\:]+', '', text.lower())

    @staticmethod
    def clean_amount(text):
        replacements = {
            'O': '0', 'o': '0',
            'I': '1', 'l': '1', '|': '1',
            'S': '5', 's': '5',
            'B': '8',
            ',': '',
            ' ': '',
            '$': '',
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        match = re.search(r'\d+(\.\d{2})?', text)
        return match.group(0) if match else None

    def find_label_bbox(self, results, label_variants):
        found = []
        for poly, text, conf in results:
            bbox = self.polygon_to_bbox(poly)
            cleaned = self.clean_text(text)
            for label in label_variants:
                if label.replace(" ", "") in cleaned:
                    found.append((bbox, text))
                    break
        return found

    def find_values_near_label_multiple(self, results, label_bbox, max_x_dist=350, max_y_dist=60):
        x_min_l, y_min_l, x_max_l, y_max_l = label_bbox
        label_y_center = (y_min_l + y_max_l) / 2
        candidates = []
        for poly, text, conf in results:
            bbox = self.polygon_to_bbox(poly)
            x_min, y_min, x_max, y_max = bbox
            text_y_center = (y_min + y_max) / 2
            vertical_diff = abs(text_y_center - label_y_center)
            if vertical_diff > max_y_dist:
                continue
            if x_min < x_max_l:
                continue
            horizontal_diff = x_min - x_max_l
            if horizontal_diff > max_x_dist:
                continue
            candidates.append(text.strip())
        return candidates
    
    def find_value_near_label(self, results, label_bbox, max_x_dist=250, max_y_dist=40):
        x_min_l, y_min_l, x_max_l, y_max_l = label_bbox
        label_y_center = (y_min_l + y_max_l) / 2
        candidates = []
        for poly, text, conf in results:
            bbox = self.polygon_to_bbox(poly)
            x_min, y_min, x_max, y_max = bbox
            text_y_center = (y_min + y_max) / 2
            vertical_diff = abs(text_y_center - label_y_center)
            if vertical_diff > max_y_dist:
                continue
            if x_min < x_max_l:
                continue
            horizontal_diff = x_min - x_max_l
            if horizontal_diff > max_x_dist:
                continue
            candidates.append((horizontal_diff, text, conf))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], -x[2]))
        return candidates[0][1]

    def extract_invoice_number(self, results):
        labels = self.find_label_bbox(results, self.invoice_number_labels)
        print("Invoice labels found:", [text for _, text in labels])
        if not labels:
            all_texts = [text for _, text, _ in results]
            for text in all_texts:
                candidate = re.sub(r'\s+', '', text)
                if re.match(r'^[A-Za-z0-9\-\/]{4,20}$', candidate):
                    return candidate
            return "Not found"
        bbox, label_text = labels[0]
        value_candidates = []
        for candidate in self.find_values_near_label_multiple(results, bbox, max_x_dist=250, max_y_dist=40):
            cleaned = re.sub(r'\s+', '', candidate)
            if re.match(r'^[A-Za-z0-9\-\/]{4,20}$', cleaned):
                value_candidates.append(cleaned)
        if value_candidates:
            return value_candidates[0]
        value = self.find_value_near_label(results, bbox, max_x_dist=350, max_y_dist=60)
        if value:
            cleaned = re.sub(r'\s+', '', value)
            if re.match(r'^[A-Za-z0-9\-\/]{4,20}$', cleaned):
                return cleaned
            return value
        return "Not found"

    def extract_date(self, results):
        labels = self.find_label_bbox(results, self.date_labels)
        if not labels:
            return "Not found"
        invoice_date_label = next(((b, t) for b, t in labels if "invoicedate" in self.clean_text(t)), None)
        bbox, label_text = invoice_date_label if invoice_date_label else labels[0]
        value = self.find_value_near_label(results, bbox)
        if not value:
            return "Not found"
        value = value.replace('J', '/').replace('l', '1').replace('O', '0')
        try:
            dt = parser.parse(value, fuzzy=True, dayfirst=False)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return "Not found"

    @staticmethod    
    def normalize_money_text(text):
        text = text.strip()
        if len(text) > 1 and text[0] in ['5', 'S', 's'] and re.match(r'[\d\.,]', text[1]):
            text = '$' + text[1:]
        text = text.replace('S', '$').replace('s', '$')  
        text = text.replace('O', '0').replace('o', '0')
        text = re.sub(r'[lI|]', '1', text)
        text = text.replace(' ', '')
        return text

    def extract_total_amount(self, results):
        labels = self.find_label_bbox(results, self.total_labels)
        if not labels:
            return "Not found"
        bbox, label_text = labels[0]
        value_text = self.find_value_near_label(results, bbox)
        if not value_text:
            return "Not found"
        cleaned = self.normalize_money_text(value_text)
        cleaned = cleaned.replace(',', '')
        match = re.search(r'\$?(\d+(\.\d{2})?)', cleaned)
        if match:
            return match.group(1)
        return "Not found"

    def extract(self, pil_image):
        processed = self.preprocess_image(pil_image)
        results = self.reader.readtext(processed)
        if not results:
            return {"Error": "No text detected"}
        invoice_number = self.extract_invoice_number(results)
        invoice_date = self.extract_date(results)
        total_amount = self.extract_total_amount(results)
        return {
            "Invoice Number": invoice_number,
            "Date": invoice_date,
            "Total Amount": total_amount,
        }
