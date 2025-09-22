PROGRAM pro1
  VAR_INPUT
    Reset : BOOL := False;
  END_VAR
  VAR
    Cnt : INT := 0;
    Out : INT := 0;
    ResetCounterValue : INT := 0;
  END_VAR

  IF Reset THEN
    Cnt := ResetCounterValue;
  ELSE
    Cnt := Cnt + 1;
  END_IF;

  Out := Cnt;
END_PROGRAM


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms,PRIORITY := 0);
    PROGRAM instance0 WITH task0 : program0;
  END_RESOURCE
END_CONFIGURATION
