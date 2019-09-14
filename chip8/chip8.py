# -*- coding: utf-8 -*-
"""
	CHIP-8 Emulator
	
	This is a project of emulator for the Chip-8 machine.
    
    Reference:
    http://devernay.free.fr/hacks/chip8/C8TECH10.HTM
"""

## -------- COMMAND LINE ARGUMENTS ---------------------------
## https://docs.python.org/3.7/howto/argparse.html
import argparse
CmdLineArgParser = argparse.ArgumentParser()
CmdLineArgParser.add_argument(
	"-v",
	"--verbose",
	help = "display debug messages in console",
	action = "store_true",
)
CmdLineArgs = CmdLineArgParser.parse_args()

## -------- LOGGING INITIALISATION ---------------------------
import misc
misc.MyLoggersObj.SetConsoleVerbosity(ConsoleVerbosity = {True : "DEBUG", False : "INFO"}[CmdLineArgs.verbose])
LOG, handle_retval_and_log = misc.CreateLogger(__name__)

import os
os.chdir(os.path.dirname(os.path.realpath(__file__)))

try:
	
	## -------------------------------------------------------
	## THE MAIN PROGRAM STARTS HERE
	## -------------------------------------------------------	

    import os
    import pygame
    import time
    import threading
    import queue
    import random
    import numpy as np
    import copy

    pygame.mixer.init(buffer = 256)
    beep = pygame.mixer.Sound(file = r'sounds\200.wav')

    class Chip8(object):

        def __init__(self, RomPath = None):
            
            self.disp_w_px = 64
            self.disp_h_px = 32
            
            with open(RomPath, 'rb') as f:
                rom_bytes = f.read()
            self.mem = (
                bytearray(0x200*[0x00]) +
                rom_bytes +
                bytearray((0x1000-len(rom_bytes)-0x200)*[0x00])
            )
            self.V = {}
            for i in range(16):
                self.V[i] = 0x00

            self.KEYS = {}
            for i in range(16):
                self.KEYS[i] = False           
                
            self.STACK = 16*[0x0000]
            
            self.extra_w = 16
            self.extra_h = 16
            self.DISPLAY = np.array([[False]*(self.disp_w_px+self.extra_w)]*(self.disp_h_px+self.extra_h))
                
            self.I = 0x00    

            self.SP = 0x0
            
            self.PC = 0x200
            
            self.DT = 0x00
            
            self.ST = 0x00
            self.bBeepPlaying = False
            
            self.EmulationThread = threading.Thread(target = self.runEmulationThread)
            self.bEmulationThreadAbortQueue = queue.Queue()
            
            self.DtStThread = threading.Thread(target = self.runDtStThread)
            self.bDtStThreadAbortQueue = queue.Queue()
        
        def runEmulationThread(self):
        
            ClockFrequency = 100000
            TimeElapsed = 0
            startTime = 0
            while True:
                
                try:
                    bEmulationThreadAbort = self.bEmulationThreadAbortQueue.get(block = False)
                    if bEmulationThreadAbort:
                        break
                except queue.Empty:
                    pass         
                
                TimeElapsed = time.perf_counter() - startTime
                if TimeElapsed > ( 1/ClockFrequency ):
                    startTime = time.perf_counter()
                    self.emulateCycle()
                else:
                    time.sleep(1/ClockFrequency - TimeElapsed)    
                    
        def runDtStThread(self):
        
            ClockFrequency = 60
            TimeElapsed = 0
            startTime = time.perf_counter()
            while True:
                
                try:
                    bAbort = self.bDtStThreadAbortQueue.get(block = False)
                    if bAbort:
                        break
                except queue.Empty:
                    pass         
                
                TimeElapsed = time.perf_counter() - startTime
                if TimeElapsed > ( 1/ClockFrequency ):
                    startTime = time.perf_counter()
                    self.decrement_DT_ST()
                else:
                    time.sleep(1/ClockFrequency - TimeElapsed)

        def emulateCycle(self):
            
            w = (self.mem[self.PC] << 8) + self.mem[self.PC+1]
            
            ### DEBUG
            ### =====
            # print("${:04X} {:04X}".format(self.PC, w))
            # print(
                # "V "+
                # " ".join(["{:02X}".format(val) for key, val in self.V.items()])+
                # "  I {:04X}".format(self.I)+
                # "  DT {:02X}".format(self.DT)
            # )
            # print(        
                # "S "+
                # " ".join(["{:04X}".format(add) for add in self.STACK])+
                # "  SP {:02X}".format(self.SP)
            # )
            
            n3 = (w & 0xF000) >> 12
            x = (w & 0x0F00) >> 8
            y = (w & 0x00F0) >> 4
            n = w & 0x000F
            kk = w & 0x00FF
            nnn = w & 0x0FFF
            
            if ( n3 == 0x0 ) and ( nnn == 0x0E0 ):
                """
                00E0 - CLS
                Clear the display.
                """
                self.DISPLAY = np.array([[False]*(self.disp_w_px+self.extra_w)]*(self.disp_h_px+self.extra_h))
            elif ( n3 == 0x0 ) and (nnn != 0x0EE):
                """
                0nnn - SYS addr
                Jump to a machine code routine at nnn.

                This instruction is only used on the old computers on which Chip-8 was originally implemented. It is ignored by modern interpreters.
                """
                pass    
            elif ( n3 == 0x0 ) and (nnn == 0x0EE):
                """
                00EE - RET
                Return from a subroutine.

                The interpreter sets the program counter to the address at the top of the stack, then subtracts 1 from the stack pointer.
                """
                self.PC = self.STACK[self.SP]
                self.SP -= 1
            elif ( n3 == 0x1 ):
                """
                1nnn - JP addr
                Jump to location nnn.
                
                The interpreter sets the program counter to nnn.
                """
                self.PC = nnn
                return
            elif ( n3 == 0x2 ):
                """
                2nnn - CALL addr
                Call subroutine at nnn.

                The interpreter increments the stack pointer, then puts the current PC on the top of the stack. The PC is then set to nnn.
                """
                self.SP += 1
                self.STACK[self.SP] = self.PC
                self.PC = nnn
                return
            elif ( n3 == 0x3 ):
                """
                3xkk - SE Vx, byte
                Skip next instruction if Vx = kk.

                The interpreter compares register Vx to kk, and if they are equal, increments the program counter by 2.
                """
                if self.V[x] == kk:
                    self.PC += 2       
            elif ( n3 == 0x4 ):
                """
                4xkk - SNE Vx, byte
                Skip next instruction if Vx != kk.

                The interpreter compares register Vx to kk, and if they are not equal, increments the program counter by 2.
                """
                if self.V[x] != kk:
                    self.PC += 2       
            elif ( n3 == 0x6 ):
                """
                6xkk - LD Vx, byte
                Set Vx = kk.
                
                The interpreter puts the value kk into register Vx.
                """
                self.V[x] = kk
            elif ( n3 == 0x7 ):
                """
                7xkk - ADD Vx, byte
                Set Vx = Vx + kk.

                Adds the value kk to the value of register Vx, then stores the result in Vx. 
                """
                self.V[x] = (self.V[x] + kk) & 0xFF
            elif ( n3 == 0x8 ) and ( n == 0x0 ):
                """
                8xy0 - LD Vx, Vy
                Set Vx = Vy.

                Stores the value of register Vy in register Vx.
                """
                self.V[x] = self.V[y]
            elif ( n3 == 0x8 ) and ( n == 0x2 ):
                """
                8xy2 - AND Vx, Vy
                Set Vx = Vx AND Vy.

                Performs a bitwise AND on the values of Vx and Vy, then stores the result in Vx. A bitwise AND compares the corrseponding bits from two values, and if both bits are 1, then the same bit in the result is also 1. Otherwise, it is 0.
                """
                self.V[x] &= self.V[y]
            elif ( n3 == 0x8 ) and ( n == 0x3 ):
                """
                8xy3 - XOR Vx, Vy
                Set Vx = Vx XOR Vy.

                Performs a bitwise exclusive OR on the values of Vx and Vy, then stores the result in Vx. An exclusive OR compares the corrseponding bits from two values, and if the bits are not both the same, then the corresponding bit in the result is set to 1. Otherwise, it is 0.
                """
                self.V[x] ^= self.V[y]
            elif ( n3 == 0x8 ) and ( n == 0x4 ):
                """
                8xy4 - ADD Vx, Vy
                Set Vx = Vx + Vy, set VF = carry.

                The values of Vx and Vy are added together. If the result is greater than 8 bits (i.e., > 255,) VF is set to 1, otherwise 0. Only the lowest 8 bits of the result are kept, and stored in Vx.
                """
                sum = self.V[x] + self.V[y]
                if sum > 0xFF:
                    self.V[0xF] = 1
                else:
                    self.V[0xF] = 0                
                self.V[x] = sum & 0xFF
            elif ( n3 == 0x8 ) and ( n == 0x5 ):
                """
                8xy5 - SUB Vx, Vy
                Set Vx = Vx - Vy, set VF = NOT borrow.

                If Vx > Vy, then VF is set to 1, otherwise 0. Then Vy is subtracted from Vx, and the results stored in Vx.
                """
                if self.V[x] > self.V[y]:
                    self.V[0xF] = 1
                else:
                    self.V[0xF] = 0               
                self.V[x] = (self.V[x] - self.V[y]) & 0xFF
            elif ( n3 == 0x8 ) and ( n == 0x6 ):
                """
                8xy6 - SHR Vx {, Vy}
                Set Vx = Vx SHR 1.

                If the least-significant bit of Vx is 1, then VF is set to 1, otherwise 0. Then Vx is divided by 2.
                """
                if self.V[x] & 0x1 == 1:
                    self.V[0xF] = 1
                else:
                    self.V[0xF] = 0
                   
                self.V[x] >>= 1
            elif ( n3 == 0xA ):
                """
                Annn - LD I, addr
                Set I = nnn.
                
                The value of register I is set to nnn.
                """
                self.I = nnn
            elif ( n3 == 0xC ):
                """
                Cxkk - RND Vx, byte
                Set Vx = random byte AND kk.

                The interpreter generates a random number from 0 to 255,
                which is then ANDed with the value kk.
                The results are stored in Vx.
                See instruction 8xy2 for more information on AND.
                """
                rr = random.randint(0, 0xFF)
                self.V[x] = rr & kk
            elif ( n3 == 0xD ):
                """
                Dxyn - DRW Vx, Vy, nibble
                Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision.

                The interpreter reads n bytes from memory, starting at the address stored in I.
                These bytes are then displayed as sprites on screen at coordinates (Vx, Vy).
                Sprites are XORed onto the existing screen. If this causes any pixels to be erased, VF is set to 1, otherwise it is set to 0.
                If the sprite is positioned so part of it is outside the coordinates of the display, it wraps around to the opposite side of the screen.
                See instruction 8xy3 for more information on XOR, and section 2.4, Display, for more information on the Chip-8 screen and sprites.
                """
                Vx = self.V[x]
                Vy = self.V[y]
                sprite_byte_list = self.mem[self.I:self.I+n]
                self.V[0xF] = 0
                w, h = self.disp_w_px, self.disp_h_px
                sprite_w = 8
                
                # remember current display
                DISPLAY_OLD = copy.copy(self.DISPLAY)
                # print sprites
                def print_sprites(sprite_byte_list, Vx, Vy):
                    for sprite_byte_index, sprite_byte in enumerate(sprite_byte_list):
                        self.DISPLAY[Vy%h+sprite_byte_index, Vx%w:Vx%w+8] ^= np.where(np.array(list(("{:8b}".format(sprite_byte)))) == '1', True, False)
                print_sprites(sprite_byte_list, Vx, Vy)
                # Wrap around if necessary
                if (h - Vy%h) < n:
                    mm = n - (h - Vy%h)
                    wrap_spr_h_list = sprite_byte_list[mm:]
                    print_sprites(wrap_spr_h_list, Vx, 0)
                if (w - Vx%w) < sprite_w:
                    ii = w - Vx%w
                    wrap_spr_w_list = [( (sb << ii) & 0xFF ) for sb in sprite_byte_list]
                    print_sprites(wrap_spr_w_list, 0, Vy)
                # Determine if any pixel was erased
                if (DISPLAY_OLD[:self.disp_h_px, :self.disp_w_px] & ~self.DISPLAY[:self.disp_h_px, :self.disp_w_px]).flatten().any():
                    self.V[0xF] = 1
                
                ### Debug DISPLAY
                ### =============
                # print()
                # for row in self.DISPLAY[:self.disp_h_px, :self.disp_w_px]:
                    # # import pdb; pdb.set_trace()
                    # print("".join(row.astype(int).astype(str)))
                # time.sleep(0.04)
                
            elif ( n3 == 0xE ) and ( kk == 0x9E ):
                """
                Ex9E - SKP Vx
                Skip next instruction if key with the value of Vx is pressed.

                Checks the keyboard, and if the key corresponding to the value of Vx is currently in the down position, PC is increased by 2.
                """
                if self.KEYS[self.V[x]]:
                    self.PC += 2
            elif ( n3 == 0xE ) and ( kk == 0xA1 ):
                """
                ExA1 - SKNP Vx
                Skip next instruction if key with the value of Vx is not pressed.

                Checks the keyboard, and if the key corresponding to the value of Vx is currently in the up position, PC is increased by 2.
                """
                if not self.KEYS[self.V[x]]:
                    self.PC += 2
            elif ( n3 == 0xF ) and ( kk == 0x07 ):
                """
                Fx07 - LD Vx, DT
                Set Vx = delay timer value.

                The value of DT is placed into Vx.
                """
                self.V[x] = self.DT
            elif ( n3 == 0xF ) and ( kk == 0x0A ):
                """
                Fx0A - LD Vx, K
                Wait for a key press, store the value of the key in Vx.

                All execution stops until a key is pressed, then the value of that key is stored in Vx.
                """
                for k_ in self.KEYS:
                    if self.KEYS[k_]:
                        break
                else:
                    return
                self.V[x] = k_
            elif ( n3 == 0xF ) and ( kk == 0x15 ):
                """
                Fx15 - LD DT, Vx
                Set delay timer = Vx.

                DT is set equal to the value of Vx.
                """
                self.DT = self.V[x]
            elif ( n3 == 0xF ) and ( kk == 0x18 ):
                """
                Fx18 - LD ST, Vx
                Set sound timer = Vx.

                ST is set equal to the value of Vx.
                """
                self.ST = self.V[x]
            elif ( n3 == 0xF ) and ( kk == 0x1E ):
                """
                Fx1E - ADD I, Vx
                Set I = I + Vx.

                The values of I and Vx are added, and the results are stored in I.
                """
                self.I += self.V[x]
            elif ( n3 == 0xF ) and ( kk == 0x33 ):
                """
                Fx33 - LD B, Vx
                Store BCD representation of Vx in memory locations I, I+1, and I+2.

                The interpreter takes the decimal value of Vx,
                and places the hundreds digit in memory at location in I,
                the tens digit at location I+1,
                and the ones digit at location I+2.
                """
                self.mem[self.I  ] = self.V[x]//100
                self.mem[self.I+1] = self.V[x]//10
                self.mem[self.I+2] = self.V[x]%10
            elif ( n3 == 0xF ) and ( kk == 0x65 ):
                """
                Fx65 - LD Vx, [I]
                Read registers V0 through Vx from memory starting at location I.

                The interpreter reads values from memory starting at location I into registers V0 through Vx.
                """
                for loc in range(x+1):
                    self.V[loc] = self.mem[self.I + loc]
            else:
                ### DEBUG
                ### =====
                print("${:04X} {:04X}".format(self.PC, w))
                print(
                    "V "+
                    " ".join(["{:02X}".format(val) for key, val in self.V.items()])+
                    "  I {:04X}".format(self.I)+
                    "  DT {:02X}".format(self.DT)
                )
                print(        
                    "S "+
                    " ".join(["{:04X}".format(add) for add in self.STACK])+
                    "  SP {:02X}".format(self.SP)
                )
                import pdb; pdb.set_trace() 
            self.PC += 2

        def decrement_DT_ST(self):
        
            if self.DT > 0:
                self.DT -= 1
            else:
                self.DT = 0x00
                
            if self.ST > 0:
                if not self.bBeepPlaying:
                    beep.play(loops = -1)
                    self.bBeepPlaying = True
                self.ST -= 1
            else:
                if self.bBeepPlaying:
                    beep.stop()
                    self.bBeepPlaying = False
                self.ST = 0x00
        
        def startAllThreads(self):
            self.EmulationThread.start()
            self.DtStThread.start()
        
        def abortAllThreads(self):
            self.bEmulationThreadAbortQueue.put(True)
            self.bDtStThreadAbortQueue.put(True)
        
        def joinAllThreads(self):
            self.EmulationThread.join()
            self.DtStThread.join()
        
        def stopAllThreads(self):
            self.abortAllThreads()
            self.joinAllThreads()
            
    ThisFolder = os.path.dirname(os.path.realpath(__file__))
    # RomPath = os.path.join(ThisFolder, r"roms\INVADERS")
    RomPath = os.path.join(ThisFolder, r"roms\WIPEOFF")

    chip8 = Chip8(RomPath = RomPath)

    zoom = 12

    screen_width = chip8.disp_w_px*zoom
    screen_height = chip8.disp_h_px*zoom

    BLACK_COLOUR = (0, 0, 0)
    WHITE_COLOUR = (255, 255, 255)

    pygame.init()
    screen = pygame.display.set_mode((screen_width, screen_height))
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    clock = pygame.time.Clock()
    FPS = 20
    bPlaying = True

    keymap = {}

    MaxTime = 0
    AverageTime = 0
    CycleCount = 0

    chip8.startAllThreads()
    while bPlaying:
        
        milliseconds = clock.tick(FPS)  # milliseconds passed since last frame
        seconds = milliseconds / 1000.0 # seconds passed since last frame (float)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                bPlaying = False # pygame window closed by user
                chip8.stopAllThreads()
            elif event.type == pygame.KEYDOWN:          
                # print(event.unicode+" DOWN")
                keymap[event.scancode] = event.unicode
                
                #======================
                # FRENCH
                #======================
                
                # if   event.unicode == "&": chip8.KEYS[0x1] = True
                # elif event.unicode == "é": chip8.KEYS[0x2] = True
                # elif event.unicode == '"': chip8.KEYS[0x3] = True
                # elif event.unicode == "'": chip8.KEYS[0xC] = True
                # elif event.unicode == "a": chip8.KEYS[0x4] = True
                # elif event.unicode == "z": chip8.KEYS[0x5] = True
                # elif event.unicode == "e": chip8.KEYS[0x6] = True
                # elif event.unicode == "r": chip8.KEYS[0xD] = True
                # elif event.unicode == "q": chip8.KEYS[0x7] = True
                # elif event.unicode == "s": chip8.KEYS[0x8] = True
                # elif event.unicode == "d": chip8.KEYS[0x9] = True
                # elif event.unicode == "f": chip8.KEYS[0xE] = True
                # elif event.unicode == "w": chip8.KEYS[0xA] = True
                # elif event.unicode == "x": chip8.KEYS[0x0] = True
                # elif event.unicode == "c": chip8.KEYS[0xB] = True
                # elif event.unicode == "v": chip8.KEYS[0xF] = True
                
                #======================
                # EN-US
                #======================                
                
                if   event.unicode == "1": chip8.KEYS[0x1] = True
                elif event.unicode == "2": chip8.KEYS[0x2] = True
                elif event.unicode == '3': chip8.KEYS[0x3] = True
                elif event.unicode == "4": chip8.KEYS[0xC] = True
                elif event.unicode == "q": chip8.KEYS[0x4] = True
                elif event.unicode == "w": chip8.KEYS[0x5] = True
                elif event.unicode == "e": chip8.KEYS[0x6] = True
                elif event.unicode == "r": chip8.KEYS[0xD] = True
                elif event.unicode == "a": chip8.KEYS[0x7] = True
                elif event.unicode == "s": chip8.KEYS[0x8] = True
                elif event.unicode == "d": chip8.KEYS[0x9] = True
                elif event.unicode == "f": chip8.KEYS[0xE] = True
                elif event.unicode == "z": chip8.KEYS[0xA] = True
                elif event.unicode == "x": chip8.KEYS[0x0] = True
                elif event.unicode == "c": chip8.KEYS[0xB] = True
                elif event.unicode == "v": chip8.KEYS[0xF] = True                
            elif event.type == pygame.KEYUP:          
                event.unicode = keymap[event.scancode]
                # print(event.unicode+" UP")
                
                #======================
                # FRENCH
                #======================                
                
                # if   event.unicode == "&": chip8.KEYS[0x1] = False
                # elif event.unicode == "é": chip8.KEYS[0x2] = False
                # elif event.unicode == '"': chip8.KEYS[0x3] = False
                # elif event.unicode == "'": chip8.KEYS[0xC] = False
                # elif event.unicode == "a": chip8.KEYS[0x4] = False
                # elif event.unicode == "z": chip8.KEYS[0x5] = False
                # elif event.unicode == "e": chip8.KEYS[0x6] = False
                # elif event.unicode == "r": chip8.KEYS[0xD] = False
                # elif event.unicode == "q": chip8.KEYS[0x7] = False
                # elif event.unicode == "s": chip8.KEYS[0x8] = False
                # elif event.unicode == "d": chip8.KEYS[0x9] = False
                # elif event.unicode == "f": chip8.KEYS[0xE] = False
                # elif event.unicode == "w": chip8.KEYS[0xA] = False
                # elif event.unicode == "x": chip8.KEYS[0x0] = False
                # elif event.unicode == "c": chip8.KEYS[0xB] = False
                # elif event.unicode == "v": chip8.KEYS[0xF] = False

                #======================
                # EN-US
                #====================== 
                
                if   event.unicode == "1": chip8.KEYS[0x1] = False
                elif event.unicode == "2": chip8.KEYS[0x2] = False
                elif event.unicode == '3': chip8.KEYS[0x3] = False
                elif event.unicode == "4": chip8.KEYS[0xC] = False
                elif event.unicode == "q": chip8.KEYS[0x4] = False
                elif event.unicode == "w": chip8.KEYS[0x5] = False
                elif event.unicode == "e": chip8.KEYS[0x6] = False
                elif event.unicode == "r": chip8.KEYS[0xD] = False
                elif event.unicode == "a": chip8.KEYS[0x7] = False
                elif event.unicode == "s": chip8.KEYS[0x8] = False
                elif event.unicode == "d": chip8.KEYS[0x9] = False
                elif event.unicode == "f": chip8.KEYS[0xE] = False
                elif event.unicode == "z": chip8.KEYS[0xA] = False
                elif event.unicode == "x": chip8.KEYS[0x0] = False
                elif event.unicode == "c": chip8.KEYS[0xB] = False
                elif event.unicode == "v": chip8.KEYS[0xF] = False                
        background.fill(BLACK_COLOUR)
        for py, pixel_row in enumerate(chip8.DISPLAY[:chip8.disp_h_px, :chip8.disp_w_px]):
            for px, pixel_state in enumerate(pixel_row):
                if pixel_state:
                    pygame.draw.rect(
                        background,
                        WHITE_COLOUR,
                        (zoom*px, zoom*py, zoom, zoom),
                    )
        screen.blit(background, (0, 0))
        pygame.display.flip()

## -------- SOMETHING WENT WRONG -----------------------------	
except:

	import traceback
	LOG.error("Something went wrong! Exception details:\n{}".format(traceback.format_exc()))

## -------- GIVE THE USER A CHANCE TO READ MESSAGES-----------
finally:
	
	input("Press any key to exit ...")
