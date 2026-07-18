"""
utils/qr_utils.py

Two independent pieces here:
1. generate_qr_code() -- makes a QR image with a book title label
   underneath, called when a book is added (books/book_service.py).
2. scan_qr_code() -- opens the laptop camera in its own window,
   watches for a QR code, and returns the decoded text once found.
   Called from the Issue Book screen.

Kept together in one utils file (not split into two) since both are
small, and "QR code handling" is one coherent piece of functionality
that different modules (books, issue_return) both need.
"""

import logging
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# prefix so scanned QR data can be validated as "this actually came
# from our system" rather than blindly trusting any scanned string as
# a book_id -- see decode_book_id_from_qr_data()
QR_DATA_PREFIX = "LMS-BOOK-"


def generate_qr_code(book_id: int, title: str, save_path: str) -> None:
    """
    Generates a QR code encoding "LMS-BOOK-<id>", with the book title
    printed as a label underneath (for when it's printed and stuck on
    a physical book -- a human can read the title even without
    scanning it). Saves the result as a PNG at save_path.
    """
    qr_data = f"{QR_DATA_PREFIX}{book_id}"

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # add a white strip below the QR code with the title printed on
    # it -- create a taller blank canvas, paste the QR at the top,
    # then draw text in the extra space at the bottom
    label_height = 40
    canvas = Image.new(
        "RGB", (qr_image.width, qr_image.height + label_height), "white"
    )
    canvas.paste(qr_image, (0, 0))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # truncate long titles so they don't overflow the image width
    display_title = title if len(title) <= 30 else title[:27] + "..."

    text_bbox = draw.textbbox((0, 0), display_title, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = max(0, (canvas.width - text_width) // 2)
    text_y = qr_image.height + 10

    draw.text((text_x, text_y), display_title, fill="black", font=font)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    canvas.save(save_path)

    logger.info("QR code generated for book_id=%s at %s", book_id, save_path)


def decode_book_id_from_qr_data(qr_data: str):
    """
    Validates that scanned QR data actually came from OUR system
    (has the expected prefix) before trusting it as a book_id.
    Returns the integer book_id, or None if the data doesn't match
    the expected format -- e.g. someone scanned a random unrelated QR
    code (a website URL, a WiFi QR, etc).
    """
    if not qr_data or not qr_data.startswith(QR_DATA_PREFIX):
        return None

    id_part = qr_data[len(QR_DATA_PREFIX):]
    if not id_part.isdigit():
        return None

    return int(id_part)


def scan_qr_code():
    """
    Opens the laptop's default camera in its own OpenCV window, waits
    for a QR code to be detected, then closes the window and returns
    the decoded book_id (or None if the window was closed / Esc
    pressed before anything was detected, or if a QR was found but
    didn't match our expected format).

    This BLOCKS until scanning finishes -- it's meant to be called
    from a button click, not from inside the main UI loop.
    """
    # imported here, not at the top of the file, so that importing
    # qr_utils (e.g. just to generate a QR when adding a book) doesn't
    # require opencv/pyzbar to be installed if only generation is used
    import cv2
    from pyzbar.pyzbar import decode

    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        logger.error("Could not open camera for QR scanning.")
        camera.release()
        raise RuntimeError(
            "Could not access the camera. Check that camera permission is "
            "granted to your terminal/IDE in System Settings > Privacy & "
            "Security > Camera, and that no other app is currently using it."
        )

    decoded_book_id = None

    try:
        while True:
            success, frame = camera.read()
            if not success:
                break

            barcodes = decode(frame)
            for barcode in barcodes:
                qr_data = barcode.data.decode("utf-8")
                book_id = decode_book_id_from_qr_data(qr_data)

                # draw a box around whatever QR was found, so the
                # user gets visual feedback even if it turns out to
                # be an unrecognized/invalid code
                x, y, w, h = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                if book_id is not None:
                    decoded_book_id = book_id

            cv2.imshow("Scan QR Code (press Esc to cancel)", frame)

            key = cv2.waitKey(1)
            if key == 27 or decoded_book_id is not None:  # Esc key, or found a valid code
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

    return decoded_book_id