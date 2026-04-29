from extractors.pan import extract_pan
import json

text = """INCOMETAXDEPARTMENT =<) GOVT. OF INDIA
Raed chen een ors

Permanent Account Number Card

TF Oo ee I ee i - |

AAYPV4747R

XY

=~

“T4 / Name
SANJAY VIJAY VERGIA

foal @1 ATA / Father's Name
CHANDRA PRAKASH VIJAY VERGIA

24122020
Ora Bt ap [ P ‘ PAN Application Digitally Signed. c d Not
4 - ‘ f Cation Digita igned, Card No
Date of Birth Be Li a ( \* sd < Valid wate Physically ariel
01/12/1969 i in he"""

print(json.dumps(extract_pan(text), indent=2))
