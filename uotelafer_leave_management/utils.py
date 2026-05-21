import frappe
from io import BytesIO
from base64 import b64encode

def get_qr_code(data):
    """Generates a base64 encoded SVG QR code for the given data string"""
    from pyqrcode import create as qrcreate
    
    url = qrcreate(data)
    stream = BytesIO()
    try:
        url.svg(stream, scale=4, background="#ffffff", module_color="#000000")
        svg = stream.getvalue().decode().replace("\n", "")
        svg_base64 = b64encode(svg.encode()).decode('utf-8')
    finally:
        stream.close()
        
    return f"data:image/svg+xml;base64,{svg_base64}"

