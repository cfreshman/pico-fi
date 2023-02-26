"""
pico-bootsel: read the state of the BOOTSEL button

Credit to github@pdg137
https://github.com/micropython/micropython/issues/6852#issuecomment-1350081346
  It would be great to have the PR merged into the Micropython core. But for 
  now I have been using this inline assembly to do it, which seems to work 
  fine at least with single-core code:
  [code provided below]

This simply packages that implementation as a git repo while waiting on 
an official release

Usage:
  import bootsel
  bootsel.read_bootsel() # raw value (0 - pressed, 1 - unpressed)
  bootsel.pressed() # boolean (True - pressed, False - unpressed)
"""

def pressed():
  return not read_bootsel()

@micropython.asm_thumb
def read_bootsel():
  # disable interrupts
  cpsid(0x0)
  
  # set r2 = addr of GPIO_QSI_SS registers, at 0x40018000
  # GPIO_QSPI_SS_CTRL is at +0x0c
  # GPIO_QSPI_SS_STATUS is at +0x08
  # is there no easier way to load a 32-bit value?
  mov(r2, 0x40)
  lsl(r2, r2, 8)
  mov(r1, 0x01)
  orr(r2, r1)
  lsl(r2, r2, 8)
  mov(r1, 0x80)
  orr(r2, r1)
  lsl(r2, r2, 8)
  
  # set bit 13 (OEOVER[1]) to disable output
  mov(r1, 1)
  lsl(r1, r1, 13)
  str(r1, [r2, 0x0c])
  
  # delay about 3us
  # seems to work on the Pico - tune for your system
  mov(r0, 0x16)
  label(DELAY)
  sub(r0, 1)
  bpl(DELAY)
  
  # check GPIO_QSPI_SS_STATUS bit 17 - input value
  ldr(r0, [r2, 0x08])
  lsr(r0, r0, 17)
  mov(r1, 1)
  and_(r0, r1)
  
  # clear bit 13 to re-enable, or it crashes
  mov(r1, 0)
  str(r1, [r2, 0x0c])
  
  # re-enable interrupts
  cpsie(0x0)
