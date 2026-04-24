import re

text = """INCOMETAMDEPARIMENT 3  GOVEOFINDIA
D/MANIKANDAN Bea
DURAISAMY Oe Ee vee
16107/1986. - GERD
Permanent AccountNumber I Li een -
BNZPM250iF ies
Signature ; ee a . Ss Eo"""

def _pan_number(text: str):
    for word in text.upper().split():
        cand = re.sub(r'[^A-Z0-9]', '', word)
        if len(cand) >= 10:
            cand = cand[:10]
            letters = cand[:5].replace('0', 'O').replace('1', 'I').replace('8', 'B').replace('5', 'S')
            numbers = cand[5:9].replace('O', '0').replace('I', '1').replace('S', '5').replace('Z', '2').replace('B', '8')
            last_letter = cand[9].replace('0', 'O').replace('1', 'I').replace('5', 'S')
            pan = letters + numbers + last_letter
            if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
                return pan
    match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text.upper())
    return match.group(1) if match else None

print("PAN:", _pan_number(text))
