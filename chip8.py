# chip-8 interpreter.
import pygame
import random
import sys

try: rom_path = sys.argv[1]
except IndexError: rom_path = 'PONG.ch8' 
fonts_path = 'fonts_chip8'
debug = 'debug' in sys.argv # prints per-cycle debug info to stdout.

speed = 340 # target speed (hz)
ram = bytearray(4096) # memory.
reg = {'v':bytearray(16), 'i':0x0, 'dt':bytearray(1),
    'st':bytearray(1), 'pc':0x200} # registers, counters.
screen0, screen1 = None, None # draw to screen0, scale and output to screen1.
stack = [] # stack; stack pointer modeled by list built-ins. 
kb_map = {
    0x1:pygame.K_1, 0x2:pygame.K_2, 0x3:pygame.K_3, 0xc:pygame.K_4,
    0x4:pygame.K_q, 0x5:pygame.K_w, 0x6:pygame.K_e, 0xd:pygame.K_r,
    0x7:pygame.K_a, 0x8:pygame.K_s, 0x9:pygame.K_d, 0xe:pygame.K_f,
    0xa:pygame.K_z, 0x0:pygame.K_x, 0xb:pygame.K_c, 0xf:pygame.K_v}

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

def load_rom():
    rom = None
    rom_file = open(rom_path, 'rb');
    with open(rom_path, 'rb') as rom_file:
        rom = bytearray(rom_file.read())

    offset = reg['pc']

    for byte in rom:
        ram[offset] = byte
        offset += 1

def load_fonts():
    offset = 0x0

    with open(fonts_path, 'r') as data:
        for line in data:
            ram[offset] = int(line.strip(), 16)
            offset += 0x1

def init():
    global screen0
    global screen1
    pygame.init()
    screen0 = pygame.Surface((64, 32))
    screen1 = pygame.display.set_mode((640, 320))

    reg['dt'], reg['st'], reg['i'] = 0, 0, 0


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# SYS addr. not implemented.
def x0nnn(nnn): 
    pass

# CLS.  clear the display.
def x00e0(): 
    screen0.fill((0, 0, 0))

# RET. return from a subroutine.
def x00ee(): 
    reg['pc'] = stack.pop()

# JP addr. jump to location nnn.
def x1nnn(nnn): 
    reg['pc'] = nnn

# CALL addr. call subroutine at nnn.
def x2nnn(nnn): 
    stack.append(reg['pc']) # put current pc on stack.
    reg['pc'] = nnn # call subroutine.

# SE Vx, byte.  skip next instruction if Vx == kk.
def x3xkk(x, kk): 
    if reg['v'][x] == kk: reg['pc'] += 2

# SNE Vx, byte. skip next instruction if Vx != kk.
def x4xkk(x, kk): 
    if reg['v'][x] != kk: reg['pc'] += 2

# SE Vx, Vy.  skip next instruction if Vx == Vy.
def x5xy0(x, y): 
    if reg['v'][x] == reg['v'][y]: reg['pc'] += 2

# LD Vx, byte. set Vx = kk.
def x6xkk(x, kk): 
    reg['v'][x] = kk

# ADD Vx, byte. set Vx = Vx + kk.
def x7xkk(x, kk): 
    reg['v'][x] = (reg['v'][x] + kk) % 256

def x8xy0(x, y): # LD Vx, Vy. set Vx = Vy.
    reg['v'][x] = reg['v'][y]

# OR Vx, Vy. set Vx = Vx | Vy.
def x8xy1(x, y): 
    reg['v'][x] = reg['v'][x] | reg['v'][y]

# AND Vx, Vy. set Vx = Vx & Vy.
def x8xy2(x, y): 
    reg['v'][x] = reg['v'][x] & reg['v'][y]

# XOR Vx, Vy. set Vx = Vx XOR Vy.
def x8xy3(x, y): 
    reg['v'][x] = reg['v'][x] ^ reg['v'][y]

# ADD Vx, Vy. set Vx = Vx + Vy.  set VF = carry.
def x8xy4(x, y): 
    result = reg['v'][x] + reg['v'][y]
    if result > 255: reg['v'][0xf] = 1
    else: reg['v'][0xf] = 0
    reg['v'][x] = result % 256

# SUB Vx, Vy. set Vx = Vx - Vy. set VF = NOT borrow.
def x8xy5(x, y): 
    reg['v'][0xf] = reg['v'][x] >= reg['v'][y]
    reg['v'][x] = (reg['v'][x] - reg['v'][y]) % 256

# SHR Vx {, Vy}. set Vx = Vy SHR 1.
def x8xy6(x, y): 
    reg['v'][0xf] = reg['v'][y] & 0x1
    reg['v'][x] = reg['v'][y] >> 1

# SUBN Vx, Vy. set Vx = Vy - Vx. set VF = NOT borrow.
def x8xy7(x, y): 
    if reg['v'][y] >= reg['v'][x]: reg['v'][0xf] = 1
    else: reg['v'][0xf] = 0
    reg['v'][x] = (reg['v'][y] - reg['v'][x]) % 256

# SHL Vx {, Vy}. set Vx = Vy SHL 1.
def x8xye(x, y): 
    reg['v'][0xf] = reg['v'][y] & 0x80
    reg['v'][x] = (reg['v'][y] << 1) % 256

# SNE Vx, Vy. skip next instruction if Vx != Vy.
def x9xy0(x, y): 
    reg['pc'] += 2 * (reg['v'][x] != reg['v'][y])

# LD I, addr. set I = nnn. 
def xannn(nnn): 
    reg['i'] = nnn

# JP V0, addr. jump to location nnn + V0.
def xbnnn(nnn): 
    reg['pc'] = nnn + reg['v'][0x0]

# RND Vx, byte. set Vx = random byte AND kk.
def xcxkk(x, kk): 
    reg['v'][x] = kk & random.randint(0, 256)

# DRW Vx, Vy, n. display n-byte sprite from RAM location I ht (Vx, Vy).
# set Vf = collision.
def xdxyn(x, y, n): 
    global screen0  
    sprite = []     
    x, y = reg['v'][x], reg['v'][y] # origin.
    x_o, y_o = 0, 0 # offsets.
    c_flag = 0 # collision flag.

    for byte in ram[reg['i']:reg['i'] + n]: # load the sprite from memory.
        str_byte = '0' * (10 - len(bin(byte))) + bin(byte)[2:]
        sprite.append(str_byte)

    for line in sprite: # draw the sprite. set c_flag for collision.
        for pixel in line:
            l_x, l_y = (x + x_o) % 64, (y + y_o) % 32
            if int(pixel):
                if screen0.get_at((l_x, l_y)) == (0, 0, 0, 255):
                    screen0.set_at((l_x, l_y), (255, 255, 255, 255))
                else: 
                    screen0.set_at((l_x, l_y), (0, 0, 0, 255))
                    c_flag = 1
            x_o += 1
        x_o, y_o = 0, y_o + 1

    if c_flag == 1: reg['v'][0xf] = 1 # set Vf if collision detected.
    else: reg['v'][0xf] = 0 # else, set it to 0.

    pygame.display.flip()

# SKP Vx. skip next instruction if key with value Vx is pressed.
def xex9e(x): 
    keys = pygame.key.get_pressed()
    if keys[kb_map[reg['v'][x]]]:
        reg['pc'] += 2

# SKP Vx. skip next instruction if key with value Vx not pressed.
def xexa1(x): 
    keys = pygame.key.get_pressed()
    if not keys[kb_map[reg['v'][x]]]:
        reg['pc'] += 2

# LD Vx, DT. set Vx = delay timer value.
def xfx07(x): 
    reg['v'][x] = reg['dt']

# LD Vx, K. wait for a key press and store its value in Vx.
def xfx0a(x): 
    # waiting = True
    # while waiting:
    #     events = pygame.event.get()
    #     for event in events:
    pass

# LD DT, Vx. set delay timer = Vx.
def xfx15(x): 
    reg['dt'] = reg['v'][x]

# LD ST, Vx. set sound timer = Vx.
def xfx18(x): 
    reg['st'] = reg['v'][x]

# ADD I, Vx. set I = I + Vx.
def xfx1e(x): 
    reg['i'] = reg['i'] + reg['v'][x]

# LD F, Vx. set I = location of sprite for digit Vx.
def xfx29(x): 
    reg['i'] = reg['v'][x] * 0x5

# LD B, Vx. store BCD of Vx in memory loc I, I + 1, and I + 2.
def xfx33(x): 
    vx, i = reg['v'][x], reg['i']
    for c in range(2, -1, -1):
        ram[i + c] = vx % 10
        vx = vx / 10

# LD [I], Vx. store V0 through Vx in RAM, starting at location I.
def xfx55(x): 
    for c in range(x + 1): ram[reg['i'] + c] = reg['v'][c]
    reg['i'] += x + 1

# LD Vx, [I]. read V0 through Vx from RAM, starting at location I.
def xfx65(x): 
    for c in range(x + 1): reg['v'][c] = ram[reg['i'] + c]
    reg['i'] += x + 1


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

inst = { # instruction mask -> function
    0x0000:x0nnn, 0x00e0:x00e0, 0x00ee:x00ee, 0x1000:x1nnn, 0x2000:x2nnn,
    0x3000:x3xkk, 0x4000:x4xkk, 0x5000:x5xy0, 0x6000:x6xkk, 0x7000:x7xkk,
    0x8000:x8xy0, 0x8001:x8xy1, 0x8002:x8xy2, 0x8003:x8xy3, 0x8004:x8xy4,
    0x8005:x8xy5, 0x8006:x8xy6, 0x8007:x8xy7, 0x800e:x8xye, 0x9000:x9xy0,
    0xa000:xannn, 0xb000:xbnnn, 0xc000:xcxkk, 0xd000:xdxyn, 0xe09e:xex9e,
    0xe0a1:xexa1, 0xf007:xfx07, 0xf00a:xfx0a, 0xf015:xfx15, 0xf018:xfx18,
    0xf01e:xfx1e, 0xf029:xfx29, 0xf033:xfx33, 0xf055:xfx55, 0xf065:xfx65}

vmasks = { # opcode -> variable mask
    0x0:(), 0x1:(0xfff,), 0x2:(0xfff,), 0x3:(0xf00, 0xff), 0x4:(0xf00, 0xff),
    0x5:(0xf00, 0xf0), 0x6:(0xf00, 0xff), 0x7:(0xf00, 0xff), 0x8:(0xf00, 0xf0),
    0x9:(0xf00, 0xf0), 0xa:(0xfff,), 0xb:(0xfff,), 0xc:(0xf00, 0xff),
    0xd:(0xf00, 0xf0, 0xf), 0xe:(0xf00,), 0xf:(0xf00,)}

def decode(op): # returns [function, [args...]].
    out, args = [], []
    instructions = inst.keys() 
    vmask = vmasks[op >> 12] 

    if op & 0xffff in instructions: out.append(inst[op])
    elif op >> 12 == 0: return [inst[0], ()]
    elif op & 0xf0ff in instructions: out.append(inst[op & 0xf0ff])
    elif op & 0xf00f in instructions: out.append(inst[op & 0xf00f])
    elif op & 0xf000 in instructions: out.append(inst[op & 0xf000])

    for x in vmask:
        arg = op & x
        if 0xff ^ x == 0xfff: arg = arg >> 8
        elif 0xf ^ x == 0xff: arg = arg >> 4
        args.append(arg)

    out.append(args)
    return out

def timers(): # simple decrement.
    if reg['dt'] > 0x0: reg['dt'] -= 0x1 
    if reg['st'] > 0x0: reg['st'] -= 0x1

def cycle():
    op = decode((ram[reg['pc']] << 8) | ram[reg['pc'] + 1]) # fetch and decode.
    if debug: px = str(op[0])+' / '+str(map(hex, op[1][:]))
    reg['pc'] += 2 # advance the program counter.
    op[0](*op[1][:]) # execute.
    timers() # decrement timers.
    
    if debug:
        print px
        d0 = map(hex, [reg['pc'], reg['dt'], reg['st'], reg['i']])
        print 'pc %s  dt %s  st %s  i %s' % (d0[0], d0[1], d0[2], d0[3])
        vregs = ''
        for i in range(16):
            vregs += hex(i)[2]+":"+hex(reg['v'][i])
            vregs += ' '*(5 - len(hex(reg['v'][i])))
            if i == 7: vregs += '\n'
        print vregs+'\n'

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

if __name__ == '__main__':
    halted = False
    clock = pygame.time.Clock()
    if debug: count = 0

    init()
    load_rom()
    load_fonts()

    while not halted:
        events = pygame.event.get()
        for event in events: 
            if event.type == pygame.QUIT: halted = True
        if debug: print 'x '+str(count); count += 1

        cycle()

        pygame.transform.scale(screen0, (640, 320), screen1)
        clock.tick_busy_loop(speed)
