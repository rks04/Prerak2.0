from urllib.parse import urlencode

params = {
    "pa": "riyakshah0912@oksbi",
    "pn": "Riya",
    "am": "1",
    "cu": "INR",
    "tn": "Order 1001",
    "tr": "TXN1001"
}

upi_link = "upi://pay?" + urlencode(params)

print(upi_link)