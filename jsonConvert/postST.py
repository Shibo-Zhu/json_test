import requests

program_text = """PROGRAM program0
  VAR
    PB1 AT %IX0.0 : BOOL;
    PB2 AT %IX0.1 : BOOL;
    LAMP AT %QX0.0 : BOOL;
  END_VAR

  LAMP := NOT(PB2) AND (LAMP OR PB1);
END_PROGRAM


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms,PRIORITY := 0);
    PROGRAM instance0 WITH task0 : program0;
  END_RESOURCE
END_CONFIGURATION
"""

url = 'http://127.0.0.1:5000/run'
response = requests.post(url, data=program_text)
print(response.text)