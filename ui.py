import gradio as gr
from invoice_extractor import InvoiceExtractor

extractor = InvoiceExtractor(gpu=False)

def ocr_extract(pil_image):
    return extractor.extract(pil_image)

def build_interface():
    return gr.Interface(
        fn=ocr_extract,
        inputs=gr.Image(type="pil"),
        outputs=gr.JSON(),
        title="Invoice Extractor",
        description="Upload invoice images to extract Invoice Number, Date, and Total Amount."
    )
