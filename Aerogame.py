"""
Combate Aéreo - Força Aérea Brasileira
Versão final melhorada
Requisitos: pip install pygame PyOpenGL PyOpenGL_accelerate
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import random
import math
import sys
from collections import deque
from enum import Enum

# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
DISPLAY = (1280, 720)
screen = pygame.display.set_mode(DISPLAY, DOUBLEBUF | OPENGL)
pygame.display.set_caption("Combate Aéreo — Força Aérea Brasileira")

# Fontes
pygame.font.init()
FONT_TINY = pygame.font.Font(None, 18)
FONT_SMALL = pygame.font.Font(None, 24)
FONT_MEDIUM = pygame.font.Font(None, 36)
FONT_LARGE = pygame.font.Font(None, 52)
FONT_HUGE = pygame.font.Font(None, 80)

# ---------------------------------------------------------------------------
# Sistema de Som Sintetizado
# ---------------------------------------------------------------------------
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self._create_sounds()
    
    def _create_sounds(self):
        """Cria sons sintetizados usando ondas quadradas/senoides"""
        sample_rate = 22050
        
        # Som de tiro
        shoot_samples = self._generate_laser_sound(0.1, 800, 200)
        self.sounds['shoot'] = pygame.mixer.Sound(buffer=shoot_samples)
        self.sounds['shoot'].set_volume(0.3)
        
        # Som de explosão
        explosion_samples = self._generate_explosion_sound(0.5)
        self.sounds['explosion'] = pygame.mixer.Sound(buffer=explosion_samples)
        self.sounds['explosion'].set_volume(0.5)
        
        # Som de dano
        hit_samples = self._generate_hit_sound(0.15)
        self.sounds['hit'] = pygame.mixer.Sound(buffer=hit_samples)
        self.sounds['hit'].set_volume(0.4)
        
        # Som especial
        special_samples = self._generate_laser_sound(0.2, 400, 100)
        self.sounds['special'] = pygame.mixer.Sound(buffer=special_samples)
        self.sounds['special'].set_volume(0.6)
        
        # Som de power-up
        powerup_samples = self._generate_powerup_sound(0.3)
        self.sounds['powerup'] = pygame.mixer.Sound(buffer=powerup_samples)
        self.sounds['powerup'].set_volume(0.4)
        
        # Som de alerta
        alert_samples = self._generate_alert_sound(0.2)
        self.sounds['alert'] = pygame.mixer.Sound(buffer=alert_samples)
        self.sounds['alert'].set_volume(0.3)
    
    def _generate_laser_sound(self, duration, freq_start, freq_end):
        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            freq = freq_start + (freq_end - freq_start) * (t / duration)
            value = int(127 * math.sin(2 * math.pi * freq * t) * 
                       (1 - t/duration))
            samples.append(max(-128, min(127, value)))
        return bytes([s + 128 for s in samples])
    
    def _generate_explosion_sound(self, duration):
        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            noise = random.randint(-128, 127)
            value = int(noise * math.exp(-t * 5) * (1 - t/duration))
            samples.append(max(-128, min(127, value)))
        return bytes([s + 128 for s in samples])
    
    def _generate_hit_sound(self, duration):
        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            value = int(127 * math.sin(2 * math.pi * 200 * t) * 
                       math.exp(-t * 20))
            samples.append(max(-128, min(127, value)))
        return bytes([s + 128 for s in samples])
    
    def _generate_powerup_sound(self, duration):
        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            freq = 400 + 800 * (t / duration)
            value = int(127 * math.sin(2 * math.pi * freq * t) * 0.7)
            samples.append(max(-128, min(127, value)))
        return bytes([s + 128 for s in samples])
    
    def _generate_alert_sound(self, duration):
        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            value = int(127 * math.sin(2 * math.pi * 1000 * t) * 
                       (0.5 + 0.5 * math.sin(2 * math.pi * 10 * t)))
            samples.append(max(-128, min(127, value)))
        return bytes([s + 128 for s in samples])
    
    def play(self, sound_name):
        if sound_name in self.sounds:
            self.sounds[sound_name].play()

# ---------------------------------------------------------------------------
# OpenGL
# ---------------------------------------------------------------------------
glEnable(GL_DEPTH_TEST)
glEnable(GL_LIGHTING)
glEnable(GL_LIGHT0)
glEnable(GL_COLOR_MATERIAL)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
glShadeModel(GL_SMOOTH)

glLightfv(GL_LIGHT0, GL_POSITION, [20, 40, 20, 1])
glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.25, 1])
glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.9, 0.85, 0.75, 1])

glMatrixMode(GL_PROJECTION)
glLoadIdentity()
gluPerspective(55, DISPLAY[0] / DISPLAY[1], 0.1, 300.0)
glMatrixMode(GL_MODELVIEW)

# ---------------------------------------------------------------------------
# Display Lists para performance
# ---------------------------------------------------------------------------
class DisplayListManager:
    def __init__(self):
        self.lists = {}
        self._create_lists()
    
    def _create_lists(self):
        # Lista para o modelo da aeronave
        self.lists['aircraft'] = glGenLists(1)
        glNewList(self.lists['aircraft'], GL_COMPILE)
        self._draw_aircraft_model()
        glEndList()
        
        # Lista para o modelo do inimigo
        self.lists['enemy'] = glGenLists(1)
        glNewList(self.lists['enemy'], GL_COMPILE)
        self._draw_enemy_model()
        glEndList()
        
        # Lista para esfera
        self.lists['sphere'] = glGenLists(1)
        glNewList(self.lists['sphere'], GL_COMPILE)
        quad = gluNewQuadric()
        gluSphere(quad, 1.0, 8, 6)
        gluDeleteQuadric(quad)
        glEndList()
    
    def _draw_aircraft_model(self):
        # Fuselagem
        glColor3f(1, 1, 1)
        glPushMatrix()
        draw_box(2.4, 0.35, 0.35)
        glPopMatrix()
        
        # Nariz
        glColor3f(0.85, 0.85, 0.85)
        glPushMatrix()
        glTranslatef(1.2, 0, 0)
        glRotatef(90, 0, 1, 0)
        draw_cone(0.18, 0.7, 12)
        glPopMatrix()
        
        # Asa principal
        glColor3f(1, 1, 1)
        glPushMatrix()
        glTranslatef(-0.3, -0.05, 0)
        draw_box(1.2, 0.07, 2.4)
        glPopMatrix()
        
        # Canards
        glColor3f(0.9, 0.9, 0.9)
        glPushMatrix()
        glTranslatef(0.8, -0.02, 0)
        draw_box(0.4, 0.06, 1.0)
        glPopMatrix()
        
        # Cauda vertical
        glColor3f(1, 1, 1)
        glPushMatrix()
        glTranslatef(-0.9, 0.25, 0)
        draw_box(0.55, 0.6, 0.07)
        glPopMatrix()
        
        # Estabilizadores horizontais
        glPushMatrix()
        glTranslatef(-0.85, 0.0, 0)
        draw_box(0.42, 0.06, 1.2)
        glPopMatrix()
    
    def call_list(self, name):
        if name in self.lists:
            glCallList(self.lists[name])
    
    def _draw_enemy_model(self):
        glColor3f(1, 1, 1)
        draw_box(1.8, 0.28, 0.28)
        glPushMatrix()
        glTranslatef(-0.2, -0.03, 0)
        draw_box(0.85, 0.05, 1.7)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(-0.68, 0.17, 0)
        draw_box(0.38, 0.42, 0.05)
        glPopMatrix()

dl_manager = DisplayListManager()

# ---------------------------------------------------------------------------
# Funções úteis
# ---------------------------------------------------------------------------
def lerp(a, b, t):
    return a + (b - a) * t

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def dist3(ax, ay, az, bx, by, bz):
    return math.sqrt((ax-bx)**2 + (ay-by)**2 + (az-bz)**2)

# ---------------------------------------------------------------------------
# Sistema de texto
# ---------------------------------------------------------------------------
def create_text_texture(text, font, color=(255,255,255)):
    surf = font.render(text, True, color)
    data = pygame.image.tostring(surf, "RGBA", False)
    w, h = surf.get_size()
    
    tid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tid)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    
    return tid, w, h

def draw_text_2d(text, x, y, font=None, color=(255,255,255)):
    if font is None:
        font = FONT_SMALL
    
    tid, w, h = create_text_texture(text, font, color)
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, DISPLAY[0], 0, DISPLAY[1])
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    glColor4f(1, 1, 1, 1)
    glBindTexture(GL_TEXTURE_2D, tid)
    
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(x, y + h)
    glTexCoord2f(1, 0); glVertex2f(x + w, y + h)
    glTexCoord2f(1, 1); glVertex2f(x + w, y)
    glTexCoord2f(0, 1); glVertex2f(x, y)
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_BLEND)
    glDeleteTextures([tid])
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

def draw_text_centered(text, cx, cy, font=None, color=(255,255,255)):
    if font is None:
        font = FONT_SMALL
    surf = font.render(text, True, color)
    w, h = surf.get_size()
    draw_text_2d(text, cx - w//2, cy - h//2, font, color)

def draw_bar_2d(x, y, w, h, ratio, color=(255,0,0)):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, DISPLAY[0], 0, DISPLAY[1])
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    
    # Fundo
    glColor4f(0.15, 0.15, 0.15, 0.8)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x+w, y)
    glVertex2f(x+w, y+h)
    glVertex2f(x, y+h)
    glEnd()
    
    # Preenchimento
    if ratio > 0:
        r, g, b = color
        glColor4f(r, g, b, 0.9)
        fw = w * max(0, min(1, ratio))
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x+fw, y)
        glVertex2f(x+fw, y+h)
        glVertex2f(x, y+h)
        glEnd()
    
    # Borda
    glColor4f(1, 1, 1, 0.3)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y)
    glVertex2f(x+w, y)
    glVertex2f(x+w, y+h)
    glVertex2f(x, y+h)
    glEnd()
    
    glDisable(GL_BLEND)
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

def draw_crosshair(cx, cy, aiming=False):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, DISPLAY[0], 0, DISPLAY[1])
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    
    if aiming:
        glColor4f(0, 1, 0, 0.4)
        glBegin(GL_LINE_LOOP)
        for i in range(32):
            angle = i * 2 * math.pi / 32
            glVertex2f(cx + math.cos(angle)*40, cy + math.sin(angle)*40)
        glEnd()
        glBegin(GL_LINE_LOOP)
        for i in range(32):
            angle = i * 2 * math.pi / 32
            glVertex2f(cx + math.cos(angle)*20, cy + math.sin(angle)*20)
        glEnd()
    
    glColor4f(0, 1, 0, 0.8)
    glBegin(GL_LINES)
    glVertex2f(cx-15, cy)
    glVertex2f(cx-5, cy)
    glVertex2f(cx+5, cy)
    glVertex2f(cx+15, cy)
    glVertex2f(cx, cy-15)
    glVertex2f(cx, cy-5)
    glVertex2f(cx, cy+5)
    glVertex2f(cx, cy+15)
    glEnd()
    
    glColor4f(0, 1, 0, 0.6)
    glPointSize(3)
    glBegin(GL_POINTS)
    glVertex2f(cx, cy)
    glEnd()
    
    glDisable(GL_BLEND)
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

# ---------------------------------------------------------------------------
# Geometria 3D
# ---------------------------------------------------------------------------
def draw_box(lx, ly, lz):
    hx, hy, hz = lx/2, ly/2, lz/2
    verts = [
        ( hx, hy, hz), ( hx,-hy, hz), (-hx,-hy, hz), (-hx, hy, hz),
        ( hx, hy,-hz), ( hx,-hy,-hz), (-hx,-hy,-hz), (-hx, hy,-hz),
    ]
    normals = [(0,0,1),(0,0,-1),(1,0,0),(-1,0,0),(0,1,0),(0,-1,0)]
    faces = [(0,1,2,3),(4,5,6,7),(0,4,5,1),(3,7,6,2),(0,3,7,4),(1,2,6,5)]
    
    glBegin(GL_QUADS)
    for (a,b,c,d), n in zip(faces, normals):
        glNormal3fv(n)
        glVertex3fv(verts[a])
        glVertex3fv(verts[b])
        glVertex3fv(verts[c])
        glVertex3fv(verts[d])
    glEnd()

def draw_cone(base_r, height, slices=12):
    quad = gluNewQuadric()
    gluCylinder(quad, base_r, 0, height, slices, 1)
    gluDeleteQuadric(quad)

def draw_sphere(r, slices=10, stacks=8):
    glPushMatrix()
    glScalef(r, r, r)
    dl_manager.call_list('sphere')
    glPopMatrix()

def draw_cylinder(r1, r2, h, slices=10):
    quad = gluNewQuadric()
    gluCylinder(quad, r1, r2, h, slices, 1)
    gluDeleteQuadric(quad)

# ---------------------------------------------------------------------------
# Partículas e Efeitos
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x,y,z, vx,vy,vz, life, color, size=0.08):
        self.x,self.y,self.z = x,y,z
        self.vx,self.vy,self.vz = vx,vy,vz
        self.life = self.max_life = life
        self.r,self.g,self.b = color
        self.size = size

    def update(self):
        self.x += self.vx; self.y += self.vy; self.z += self.vz
        self.vy -= 0.008
        self.vx *= 0.98; self.vz *= 0.98
        self.life -= 1
        return self.life > 0

    def draw(self):
        a = self.life / self.max_life
        glColor4f(self.r, self.g, self.b, a)
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        draw_sphere(self.size * (0.5 + a*0.5), 6, 4)
        glPopMatrix()

class SmokeTrail:
    def __init__(self, cap=25):
        self.pts = deque(maxlen=cap)

    def add(self, x, y, z):
        self.pts.append({'x': x + random.uniform(-.05,.05),
                         'y': y + random.uniform(-.05,.05),
                         'z': z + random.uniform(-.05,.05),
                         'life': 1.0})

    def update(self):
        for p in self.pts:
            p['life'] -= 0.04
        while self.pts and self.pts[0]['life'] <= 0:
            self.pts.popleft()

    def draw(self):
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        for p in self.pts:
            a = max(0, p['life']) * 0.35
            glColor4f(0.85, 0.85, 0.85, a)
            glPushMatrix()
            glTranslatef(p['x'], p['y'], p['z'])
            draw_sphere(0.12 * p['life'], 4, 4)
            glPopMatrix()
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

# ---------------------------------------------------------------------------
# Power-ups
# ---------------------------------------------------------------------------
class PowerUpType(Enum):
    HEALTH = "health"
    SHIELD = "shield"
    AMMO = "ammo"
    SPEED = "speed"

class PowerUp:
    TYPES = {
        PowerUpType.HEALTH: {'color': (0, 1, 0), 'effect': 'Reparo'},
        PowerUpType.SHIELD: {'color': (0, 0.5, 1), 'effect': 'Escudo'},
        PowerUpType.AMMO: {'color': (1, 0.5, 0), 'effect': 'Munição'},
        PowerUpType.SPEED: {'color': (1, 1, 0), 'effect': 'Velocidade'},
    }
    
    def __init__(self, x, y, z, ptype=PowerUpType.HEALTH):
        self.x, self.y, self.z = x, y, z
        self.type = ptype
        self.life = 600  # 10 segundos a 60 FPS
        self.rotation = 0
        self.bob_offset = 0
    
    def update(self):
        self.life -= 1
        self.rotation += 2
        self.bob_offset = math.sin(self.life * 0.05) * 0.5
        return self.life > 0
    
    def apply(self, player, sound_manager):
        if self.type == PowerUpType.HEALTH:
            player.health = min(player.max_health, player.health + 1)
        elif self.type == PowerUpType.SHIELD:
            player.shield = player.max_shield
            player.shield_active = True
        elif self.type == PowerUpType.AMMO:
            player.special_ammo = player.max_special
        elif self.type == PowerUpType.SPEED:
            player.speed_boost = 120  # 2 segundos de boost
        
        sound_manager.play('powerup')
        return self.TYPES[self.type]['effect']
    
    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y + self.bob_offset, self.z)
        glRotatef(self.rotation, 0, 1, 0)
        
        r, g, b = self.TYPES[self.type]['color']
        
        # Efeito de brilho
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glow = (math.sin(self.life * 0.1) + 1) * 0.3
        glColor4f(r, g, b, glow)
        draw_sphere(0.5, 8, 6)
        
        # Núcleo
        glColor4f(r, g, b, 0.8)
        draw_sphere(0.3, 8, 6)
        
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
        
        glPopMatrix()

# ---------------------------------------------------------------------------
# Sistema de Conquistas
# ---------------------------------------------------------------------------
class Achievements:
    def __init__(self):
        self.unlocked = {}
        self.recent = []
        self.recent_timer = 0
        self._init_achievements()
    
    def _init_achievements(self):
        self.conditions = {
            'first_kill': {
                'name': 'Primeiro Abate',
                'desc': 'Abata seu primeiro inimigo',
                'icon': '🎯',
                'check': lambda g: g.player.kills >= 1
            },
            'ace': {
                'name': 'Ás da Aviação',
                'desc': 'Abata 5 inimigos',
                'icon': '⭐',
                'check': lambda g: g.player.kills >= 5
            },
            'wave5': {
                'name': 'Sobrevivente',
                'desc': 'Alcance a onda 5',
                'icon': '🛡️',
                'check': lambda g: g.wave >= 5
            },
            'wave10': {
                'name': 'Veterano',
                'desc': 'Alcance a onda 10',
                'icon': '🏆',
                'check': lambda g: g.wave >= 10
            },
            'no_damage': {
                'name': 'Intocado',
                'desc': 'Complete uma onda sem dano',
                'icon': '💎',
                'check': lambda g: g.player.health == g.player.max_health and g.wave > 3
            },
            'specialist': {
                'name': 'Especialista',
                'desc': 'Use a arma especial 3 vezes',
                'icon': '💥',
                'check': lambda g: g.player.specials_used >= 3
            },
        }
        for key in self.conditions:
            self.unlocked[key] = False
    
    def check(self, game):
        for key, achievement in self.conditions.items():
            if not self.unlocked[key] and achievement['check'](game):
                self.unlocked[key] = True
                self.recent.append(achievement)
                self.recent_timer = 180  # 3 segundos
    
    def update(self):
        if self.recent_timer > 0:
            self.recent_timer -= 1
        else:
            self.recent.clear()
    
    def draw(self):
        if self.recent:
            y = DISPLAY[1] - 100
            for achievement in self.recent[-3:]:  # Mostrar últimos 3
                alpha = min(1, self.recent_timer / 60)
                draw_text_centered(
                    f"{achievement['icon']} {achievement['name']}",
                    DISPLAY[0] // 2, y,
                    FONT_MEDIUM,
                    (int(255*alpha), int(215*alpha), 0)
                )
                y -= 30

# ---------------------------------------------------------------------------
# Aeronaves
# ---------------------------------------------------------------------------
AIRCRAFT_SPECS = {
    "F-39 Gripen": {
        "color": (0.65, 0.65, 0.68), "speed": 2.2, "maneuver": 1.9,
        "firepower": 1.6, "fire_rate": 7, "shield_regen": 0.18,
        "special": "Meteor BVRAAM", "max_special": 4, "health": 4,
        "weight": "8.5t", "engine": "GE F414-GE-39E",
        "desc": "Caca multirole 4.5 geracao. Radar AESA, supercruzeiro.",
    },
    "F-5M": {
        "color": (0.55, 0.58, 0.55), "speed": 1.7, "maneuver": 1.6,
        "firepower": 1.4, "fire_rate": 10, "shield_regen": 0.15,
        "special": "Python-4", "max_special": 3, "health": 4,
        "weight": "7.2t", "engine": "GE J85-GE-21",
        "desc": "Caca tatico leve. Modernizado com glass cockpit.",
    },
    "A-29 Super Tucano": {
        "color": (0.48, 0.50, 0.35), "speed": 1.0, "maneuver": 1.4,
        "firepower": 1.8, "fire_rate": 13, "shield_regen": 0.28,
        "special": "GBU-12 Paveway II", "max_special": 5, "health": 5,
        "weight": "5.4t", "engine": "PT6A-68/3 (1.600 hp)",
        "desc": "Ataque leve e COIN. Robusto, opera em pistas nao preparadas.",
    },
    "KC-390 Millennium": {
        "color": (0.42, 0.44, 0.62), "speed": 0.9, "maneuver": 0.7,
        "firepower": 2.2, "fire_rate": 5, "shield_regen": 0.35,
        "special": "Lancamento de Carga", "max_special": 3, "health": 6,
        "weight": "35t", "engine": "IAE V2500-E5 (x2)",
        "desc": "Transporte militar. Carga 26t, blindagem reforcada.",
    },
    "A-1 AMX": {
        "color": (0.45, 0.38, 0.32), "speed": 1.4, "maneuver": 1.5,
        "firepower": 1.7, "fire_rate": 9, "shield_regen": 0.22,
        "special": "LGB Paveway III", "max_special": 4, "health": 4,
        "weight": "10.7t", "engine": "Rolls-Royce Spey 807",
        "desc": "Caca-bombardeiro subsonico. Ataque precisao.",
    },
}

class Aircraft:
    def __init__(self, name):
        spec = AIRCRAFT_SPECS[name]
        self.name = name
        self.color = spec["color"]
        self.base_speed = spec["speed"]
        self.speed = spec["speed"]
        self.maneuver = spec["maneuver"]
        self.firepower = spec["firepower"]
        self.fire_rate = spec["fire_rate"]
        self.shield_regen = spec["shield_regen"]
        self.special_name = spec["special"]
        self.max_special = spec["max_special"]
        self.max_health = spec["health"]
        self.weight = spec["weight"]
        self.engine = spec["engine"]
        
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.rx = 0.0
        self.ry = 0.0
        self.rz = 0.0
        
        self.health = self.max_health
        self.shield = 100.0
        self.max_shield = 100.0
        self.special_ammo = self.max_special
        self.specials_used = 0
        self.score = 0
        self.kills = 0
        
        self.fire_cd = 0
        self.invuln = 0
        self.hit_flash = 0
        self.shield_active = False
        self.speed_boost = 0
        
        self.smoke = SmokeTrail()
        self.glow_phase = 0.0
        self.afterburner = False
        self.aiming = False

    def impulse(self, dx, dy, dz):
        yr = math.radians(self.ry)
        speed = self.base_speed * (1.5 if self.speed_boost > 0 else 1.0)
        self.vx += (dx * math.cos(yr) + dz * math.sin(yr)) * speed * 0.12
        self.vy += dy * speed * 0.12
        self.vz += (-dx * math.sin(yr) + dz * math.cos(yr)) * speed * 0.12

    def rotate(self, dpitch, dyaw, droll):
        self.rx = clamp(self.rx + dpitch * self.maneuver, -80, 80)
        self.ry += dyaw * self.maneuver
        self.rz = clamp(self.rz + droll * self.maneuver, -60, 60)

    def update(self):
        self.x += self.vx; self.y += self.vy; self.z += self.vz
        self.vx *= 0.93; self.vy *= 0.93; self.vz *= 0.93
        self.x = clamp(self.x, -45, 45)
        self.y = clamp(self.y, -14, 18)
        self.z = clamp(self.z, -45, 45)
        self.rz *= 0.88
        
        if self.fire_cd > 0: self.fire_cd -= 1
        if self.invuln > 0: self.invuln -= 1
        if self.hit_flash > 0: self.hit_flash -= 1
        if self.speed_boost > 0: self.speed_boost -= 1
        
        if not self.shield_active and self.shield < self.max_shield:
            self.shield = min(self.max_shield, self.shield + self.shield_regen)
        
        self.glow_phase = (self.glow_phase + 0.15) % (2*math.pi)
        
        spd = abs(self.vx)+abs(self.vy)+abs(self.vz)
        if spd > 0.3:
            yr = math.radians(self.ry)
            self.smoke.add(self.x - math.sin(yr)*1.6,
                           self.y - 0.05,
                           self.z + math.cos(yr)*1.6)
        self.smoke.update()

    def can_fire(self):
        return self.fire_cd <= 0

    def fire(self):
        if self.can_fire():
            self.fire_cd = self.fire_rate
            return True
        return False

    def take_damage(self, dmg, sound_manager):
        if self.invuln > 0: return False
        if self.shield_active:
            self.shield -= dmg * 0.4
            if self.shield <= 0:
                self.shield = 0
                self.shield_active = False
            sound_manager.play('hit')
            return True
        self.health -= 1
        self.invuln = 70
        self.hit_flash = 14
        sound_manager.play('hit')
        if self.health <= 0:
            sound_manager.play('explosion')
        return self.health <= 0

    def draw(self, flash=False):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.ry, 0, 1, 0)
        glRotatef(self.rx, 1, 0, 0)
        glRotatef(self.rz, 0, 0, 1)
        self._draw_model(flash)
        glPopMatrix()
        self.smoke.draw()

    def _draw_model(self, flash):
        r,g,b = (1,1,1) if flash and self.hit_flash>0 else self.color
        glow = abs(math.sin(self.glow_phase))
        
        # Modelo base da display list
        glColor3f(r,g,b)
        dl_manager.call_list('aircraft')
        
        # Canopy (não está na display list)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glColor4f(0.3, 0.65, 1.0, 0.55)
        glPushMatrix()
        glTranslatef(0.55, 0.24, 0)
        draw_sphere(0.21, 10, 8)
        glPopMatrix()
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
        
        # Efeito de boost de velocidade
        if self.speed_boost > 0:
            glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            boost_alpha = (math.sin(self.glow_phase * 3) + 1) * 0.3
            glColor4f(1, 1, 0, boost_alpha)
            glPushMatrix()
            glTranslatef(0, -0.3, 0)
            draw_sphere(0.8, 8, 6)
            glPopMatrix()
            glDisable(GL_BLEND)
            glEnable(GL_LIGHTING)
        
        # Motor(es) na traseira (-X)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        heat = glow * (1.4 if self.afterburner else 0.7)
        if self.afterburner:
            glColor4f(0.4, 0.6+glow*0.4, 1.0, heat*0.8)
        else:
            glColor4f(1.0, 0.55+glow*0.3, 0.0, heat*0.7)
        glPushMatrix()
        glTranslatef(-1.35, 0, 0)
        draw_sphere(0.16, 8, 6)
        glPopMatrix()
        
        if self.afterburner:
            for k in range(1, 5):
                a = heat * (1 - k*0.22)
                glColor4f(0.3, 0.5+glow*0.3, 1.0, max(0, a))
                glPushMatrix()
                glTranslatef(-1.35 - k*0.25, 0, 0)
                draw_sphere(0.12+k*0.02, 6, 4)
                glPopMatrix()
        
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

# ---------------------------------------------------------------------------
# Balas
# ---------------------------------------------------------------------------
class Bullet:
    def __init__(self, x, y, z, dx, dy, dz, damage=15, btype="normal"):
        self.x, self.y, self.z = x, y, z
        self.dx, self.dy, self.dz = dx, dy, dz
        self.damage = damage
        self.btype = btype
        self.active = True
        self.trail = deque(maxlen=10)

    def update(self):
        self.trail.append((self.x, self.y, self.z))
        self.x += self.dx; self.y += self.dy; self.z += self.dz
        if abs(self.x)>55 or abs(self.y)>35 or abs(self.z)>55:
            self.active = False

    def draw(self):
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        
        if self.btype == "special":
            cr,cg,cb = 1.0, 0.4, 0.0; sz = 0.25
        elif self.btype == "enemy":
            cr,cg,cb = 1.0, 0.15, 0.15; sz = 0.12
        else:
            cr,cg,cb = 1.0, 0.95, 0.2; sz = 0.16
        
        for i, (tx,ty,tz) in enumerate(self.trail):
            a = (i+1)/len(self.trail) * 0.5
            glColor4f(cr,cg,cb,a)
            glPushMatrix()
            glTranslatef(tx,ty,tz)
            draw_sphere(sz*(i+1)/len(self.trail)*0.8, 5, 4)
            glPopMatrix()
        
        glColor4f(cr,cg,cb,1)
        glPushMatrix()
        glTranslatef(self.x,self.y,self.z)
        draw_sphere(sz, 8, 6)
        glPopMatrix()
        
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

# ---------------------------------------------------------------------------
# Inimigos
# ---------------------------------------------------------------------------
ENEMY_TYPES = {
    "fighter": {"hp": 80, "spd": 0.60, "dmg": 10, "col": (0.80,0.20,0.20), "sz": 1.0, "pts": 100},
    "bomber": {"hp": 150, "spd": 0.28, "dmg": 25, "col": (0.55,0.18,0.55), "sz": 1.5, "pts": 220},
    "interceptor": {"hp": 60, "spd": 0.90, "dmg": 15, "col": (0.90,0.50,0.10), "sz": 0.8, "pts": 160},
    "helicopter": {"hp": 100, "spd": 0.18, "dmg": 20, "col": (0.20,0.58,0.20), "sz": 1.2, "pts": 140},
}

class Enemy:
    def __init__(self, x, y, z, etype="fighter", diff=1):
        sp = ENEMY_TYPES[etype]
        self.type = etype
        self.x, self.y, self.z = x, y, z
        self.hp = sp["hp"] * diff
        self.mhp = self.hp
        self.spd = sp["spd"]
        self.dmg = sp["dmg"]
        self.col = sp["col"]
        self.sz = sp["sz"]
        self.pts = int(sp["pts"] * diff)
        self.diff = diff
        
        self.ry = 0.0
        self.glow = 0.0
        self.hit_flash = 0
        self.shoot_cd = random.randint(40, 100)
        self.shoot_del = int(max(20, 70 / diff))
        self.mt = 0.0
        self.pat = random.choice(['circle','zigzag','straight'])
        self.state = "patrol"

    def update(self, px, py, pz):
        self.mt += 0.04
        self.glow = (self.glow + 0.18) % (2*math.pi)
        if self.hit_flash > 0: self.hit_flash -= 1
        
        dx,dy,dz = px-self.x, py-self.y, pz-self.z
        dist = dist3(self.x,self.y,self.z, px,py,pz)
        self.ry = math.degrees(math.atan2(dx, dz))
        
        if dist < 5: self.state = "evade"
        elif dist < 18: self.state = "attack"
        else: self.state = "patrol"
        
        if self.state == "patrol":
            if self.pat == 'circle':
                self.x += math.cos(self.mt)*self.spd*0.35
                self.z += math.sin(self.mt)*self.spd*0.35
            elif self.pat == 'zigzag':
                self.x += (1 if int(self.mt)%2==0 else -1)*self.spd*0.35
                self.z += self.spd*0.25
            else:
                self.z += self.spd*0.3
            self.y += math.sin(self.mt*2)*0.15
        elif self.state == "attack":
            if dist>0:
                self.x += dx/dist*self.spd*0.55
                self.y += dy/dist*self.spd*0.25
                self.z += dz/dist*self.spd*0.55
        elif self.state == "evade":
            if dist>0:
                self.x -= dx/dist*self.spd*0.8
                self.y += math.sin(self.mt*4)*0.4
                self.z -= dz/dist*self.spd*0.8
        
        self.x = clamp(self.x,-42,42)
        self.y = clamp(self.y,-13,17)
        self.z = clamp(self.z,-42,42)
        
        self.shoot_cd -= 1
        if self.shoot_cd <= 0 and dist < 28:
            self.shoot_cd = self.shoot_del
            return True
        return False

    def take_damage(self, dmg):
        self.hp -= dmg
        self.hit_flash = 6
        return self.hp <= 0

    def draw(self):
        flash = self.hit_flash > 0
        r,g,b = (1,1,1) if flash else self.col
        
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.ry, 0, 1, 0)
        glScalef(self.sz, self.sz, self.sz)
        
        glColor3f(r, g, b)
        dl_manager.call_list('enemy')
        
        # Cockpit
        glColor3f(r*0.7, g*0.3, b*0.3)
        glPushMatrix()
        glTranslatef(0.4, 0.15, 0)
        draw_sphere(0.14, 8, 6)
        glPopMatrix()
        
        # Motor
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        eg = abs(math.sin(self.glow))
        glColor4f(1, 0.4+eg*0.3, 0, 0.6*eg)
        glPushMatrix()
        glTranslatef(-1.05, 0, 0)
        draw_sphere(0.12, 6, 4)
        glPopMatrix()
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
        
        glPopMatrix()

# ---------------------------------------------------------------------------
# Explosão
# ---------------------------------------------------------------------------
class Explosion:
    def __init__(self, x, y, z, size=1.0):
        self.life = 45
        self.parts = []
        palettes = [(1,.5,0),(1,.3,0),(1,.8,0),(1,1,0)]
        
        for _ in range(int(30*size)):
            ah = random.uniform(0, 2*math.pi)
            av = random.uniform(-math.pi/2, math.pi/2)
            s = random.uniform(0.08, 0.45)*size
            self.parts.append(Particle(
                x,y,z,
                math.cos(ah)*math.cos(av)*s,
                math.sin(av)*s,
                math.sin(ah)*math.cos(av)*s,
                random.randint(20,45),
                random.choice(palettes),
                random.uniform(0.04,0.14)*size
            ))

    def update(self):
        self.life -= 1
        self.parts = [p for p in self.parts if p.update()]
        return self.life > 0 or len(self.parts) > 0

    def draw(self):
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        for p in self.parts:
            p.draw()
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

# ---------------------------------------------------------------------------
# Nuvens
# ---------------------------------------------------------------------------
class Cloud:
    def __init__(self):
        self.x = random.uniform(-45, 45)
        self.y = random.uniform(6, 16)
        self.z = random.uniform(-45, 45)
        self.r = random.uniform(2.0, 4.5)
        self.blobs = [(random.uniform(-self.r*.6,self.r*.6),
                       random.uniform(-self.r*.3,self.r*.3),
                       random.uniform(-self.r*.6,self.r*.6),
                       random.uniform(self.r*.4,self.r*.8)) for _ in range(4)]
        self.drift = random.uniform(0.002, 0.008)

    def update(self):
        self.x += self.drift
        if self.x > 50: self.x = -50

    def draw(self):
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glColor4f(1, 1, 1, 0.55)
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        draw_sphere(self.r*0.6, 8, 6)
        for bx, by, bz, br in self.blobs:
            glPushMatrix()
            glTranslatef(bx, by, bz)
            draw_sphere(br, 7, 5)
            glPopMatrix()
        glPopMatrix()
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

# ---------------------------------------------------------------------------
# Terreno e Céu
# ---------------------------------------------------------------------------
_TREE_POS = [(-32,-32),(-22,26),(16,-34),(31,21),(-11,-16),
             (26,-11),(-36,11),(11,31),(-26,-21),(36,-26)]

def draw_terrain():
    glColor3f(0.28, 0.46, 0.20)
    glNormal3f(0, 1, 0)
    glBegin(GL_QUADS)
    glVertex3f(-55, -5, -55)
    glVertex3f(-55, -5, 55)
    glVertex3f(55, -5, 55)
    glVertex3f(55, -5, -55)
    glEnd()
    
    glDisable(GL_LIGHTING)
    glColor3f(0.22, 0.38, 0.15)
    glBegin(GL_LINES)
    for i in range(-55, 56, 10):
        glVertex3f(i, -4.98, -55)
        glVertex3f(i, -4.98, 55)
        glVertex3f(-55, -4.98, i)
        glVertex3f(55, -4.98, i)
    glEnd()
    glEnable(GL_LIGHTING)
    
    for tx, tz in _TREE_POS:
        glPushMatrix()
        glTranslatef(tx, -5, tz)
        glColor3f(0.35, 0.25, 0.18)
        glPushMatrix()
        glTranslatef(0, 0.6, 0)
        draw_cylinder(0.14, 0.10, 1.2, 8)
        glPopMatrix()
        glColor3f(0.12, 0.50, 0.12)
        glPushMatrix()
        glTranslatef(0, 1.8, 0)
        draw_sphere(0.80, 7, 6)
        glPopMatrix()
        glPopMatrix()

def draw_sky():
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    
    glBegin(GL_QUADS)
    glColor3f(0.45, 0.65, 0.95)
    glVertex3f(-100, -10, -100)
    glVertex3f(-100, -10, 100)
    glColor3f(0.18, 0.32, 0.82)
    glVertex3f(100, -10, 100)
    glVertex3f(100, -10, -100)
    glEnd()
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

# ---------------------------------------------------------------------------
# Jogo Principal
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.sound_manager = SoundManager()
        self.achievements = Achievements()
        self.aircraft_names = list(AIRCRAFT_SPECS.keys())
        self.aircrafts = [Aircraft(n) for n in self.aircraft_names]
        self.player = self.aircrafts[0]
        self.bullets = []
        self.ebullets = []
        self.enemies = []
        self.explosions = []
        self.powerups = []
        self.clouds = [Cloud() for _ in range(12)]
        self.state = "SELECTION"
        self.clock = pygame.time.Clock()
        self.wave = 1
        self.diff = 1.0
        self.sel_idx = 0
        self.sel_preview_r = 0.0
        self.shake = 0
        self.shake_x = self.shake_y = 0.0
        self.cam_x = self.cam_y = self.cam_z = 0.0
        self.zoom_level = 1.0
        self.target_zoom = 1.0
        self._prev_keys = set()
        self.powerup_spawn_timer = 0
        self.wave_announce_timer = 0
        self.wave_announce_text = ""

    def spawn_wave(self):
        n = 3 + self.wave * 2
        for _ in range(n):
            x = random.uniform(-35, 35)
            y = random.uniform(-8, 8)
            z = random.uniform(-35, 35)
            et = random.choice(["fighter", "fighter", "bomber", "interceptor"])
            self.enemies.append(Enemy(x, y, z, et, self.diff))
        
        # Anunciar nova onda
        self.wave_announce_timer = 120
        self.wave_announce_text = f"ONDA {self.wave}"
        self.sound_manager.play('alert')

    def spawn_powerup(self):
        if len(self.powerups) < 3 and self.powerup_spawn_timer <= 0:
            x = random.uniform(-30, 30)
            y = random.uniform(-5, 10)
            z = random.uniform(-30, 30)
            
            # Peso das probabilidades
            weights = [0.3, 0.3, 0.2, 0.2]  # health, shield, ammo, speed
            ptype = random.choices(
                [PowerUpType.HEALTH, PowerUpType.SHIELD, 
                 PowerUpType.AMMO, PowerUpType.SPEED],
                weights=weights
            )[0]
            
            self.powerups.append(PowerUp(x, y, z, ptype))
            self.powerup_spawn_timer = random.randint(300, 600)  # 5-10 segundos

    def start_game(self, idx):
        self.player = Aircraft(self.aircraft_names[idx])
        self.bullets.clear()
        self.ebullets.clear()
        self.enemies.clear()
        self.explosions.clear()
        self.powerups.clear()
        self.wave = 1
        self.diff = 1.0
        self.cam_x = self.player.x
        self.cam_y = self.player.y + 3
        self.cam_z = self.player.z + 9
        self.zoom_level = 1.0
        self.target_zoom = 1.0
        self.powerup_spawn_timer = 300
        self.spawn_wave()
        self.state = "PLAYING"
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        cur_set = set(k for k in range(512) if keys[k])
        pressed = cur_set - self._prev_keys
        self._prev_keys = cur_set
        
        if self.state == "SELECTION":
            if K_LEFT in pressed or K_a in pressed:
                self.sel_idx = (self.sel_idx - 1) % len(self.aircraft_names)
            if K_RIGHT in pressed or K_d in pressed:
                self.sel_idx = (self.sel_idx + 1) % len(self.aircraft_names)
            for i in range(5):
                if (K_1+i) in pressed:
                    self.sel_idx = i
            if K_RETURN in pressed or K_SPACE in pressed:
                self.start_game(self.sel_idx)
            return
        
        if self.state == "GAME_OVER":
            if K_ESCAPE in pressed or K_RETURN in pressed:
                self.state = "SELECTION"
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
            return
        
        if self.state == "PAUSED":
            if K_p in pressed or K_ESCAPE in pressed:
                self.state = "PLAYING"
            return
        
        if self.state == "PLAYING":
            p = self.player
            
            # Pausa
            if K_p in pressed:
                self.state = "PAUSED"
                return
            
            if K_ESCAPE in pressed:
                self.state = "SELECTION"
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                return
            
            # Zoom
            if pygame.mouse.get_pressed()[2]:
                self.target_zoom = 2.5
                p.aiming = True
            else:
                self.target_zoom = 1.0
                p.aiming = False
            
            self.zoom_level = lerp(self.zoom_level, self.target_zoom, 0.1)
            
            # Movimento
            if keys[K_w] or keys[K_UP]:
                p.impulse(0, 0, -0.18)
                p.afterburner = True
            else:
                p.afterburner = False
            if keys[K_s] or keys[K_DOWN]: p.impulse(0, 0, 0.15)
            if keys[K_a] or keys[K_LEFT]: p.impulse(-0.15, 0, 0)
            if keys[K_d] or keys[K_RIGHT]: p.impulse(0.15, 0, 0)
            if keys[K_SPACE]: p.impulse(0, 0.15, 0)
            if keys[K_LSHIFT]: p.impulse(0, -0.15, 0)
            
            # Roll
            if keys[K_q]: p.rotate(0, 0, 3.0)
            if keys[K_e]: p.rotate(0, 0, -3.0)
            
            # Mouse aim
            mx, my = pygame.mouse.get_rel()
            sensitivity = 0.04 if p.aiming else 0.08
            p.rotate(my * sensitivity, mx * sensitivity, 0)
            
            # Tiro
            if pygame.mouse.get_pressed()[0]:
                self._shoot()
            
            # Especial
            if K_x in pressed:
                self._special()

    def _shoot(self):
        p = self.player
        if not p.fire():
            return
        
        yr = math.radians(p.ry)
        xr = math.radians(p.rx)
        
        dx = math.sin(yr) * math.cos(xr) * 2.5
        dy = -math.sin(xr) * 2.5
        dz = -math.cos(yr) * math.cos(xr) * 2.5
        
        self.bullets.append(Bullet(
            p.x + dx*0.4, p.y + dy*0.4, p.z + dz*0.4,
            dx, dy, dz,
            damage=15 * p.firepower
        ))
        
        self.sound_manager.play('shoot')

    def _special(self):
        p = self.player
        if p.special_ammo <= 0:
            return
        
        yr = math.radians(p.ry)
        xr = math.radians(p.rx)
        
        for i in range(-2, 3):
            sa = yr + i * 0.12
            dx = math.sin(sa) * math.cos(xr) * 3.5
            dy = -math.sin(xr) * 3.5
            dz = -math.cos(sa) * math.cos(xr) * 3.5
            self.bullets.append(Bullet(
                p.x, p.y, p.z,
                dx, dy, dz,
                damage=45,
                btype="special"
            ))
        
        p.special_ammo -= 1
        p.specials_used += 1
        self.shake = max(self.shake, 12)
        self.sound_manager.play('special')

    def update(self):
        if self.state != "PLAYING":
            return
            
        p = self.player
        p.update()
        
        for c in self.clouds: c.update()
        
        if self.shake > 0:
            self.shake -= 1
            amp = self.shake * 0.015
            self.shake_x = random.uniform(-amp, amp)
            self.shake_y = random.uniform(-amp, amp)
        else:
            self.shake_x = self.shake_y = 0.0
        
        # Atualizar power-ups
        self.powerup_spawn_timer -= 1
        self.spawn_powerup()
        for pu in self.powerups:
            if pu.update():
                if dist3(p.x, p.y, p.z, pu.x, pu.y, pu.z) < 2.5:
                    effect = pu.apply(p, self.sound_manager)
                    self.powerups.remove(pu)
            else:
                self.powerups.remove(pu)
        
        # Atualizar balas
        for b in self.bullets: b.update()
        self.bullets = [b for b in self.bullets if b.active]
        
        for b in self.ebullets: b.update()
        self.ebullets = [b for b in self.ebullets if b.active]
        
        # Atualizar inimigos e verificar colisões
        for e in self.enemies:
            shoot = e.update(p.x, p.y, p.z)
            if shoot:
                dx, dy, dz = p.x-e.x, p.y-e.y, p.z-e.z
                d = math.sqrt(dx*dx+dy*dy+dz*dz)
                if d > 0:
                    spd = 1.6
                    self.ebullets.append(Bullet(
                        e.x, e.y, e.z,
                        dx/d*spd, dy/d*spd, dz/d*spd,
                        damage=e.dmg, btype="enemy"
                    ))
            
            for b in self.bullets:
                if not b.active: continue
                if dist3(b.x, b.y, b.z, e.x, e.y, e.z) < 1.5 * e.sz:
                    if e.take_damage(b.damage):
                        self.explosions.append(Explosion(e.x, e.y, e.z, e.sz))
                        p.score += e.pts
                        p.kills += 1
                        self.sound_manager.play('explosion')
                    b.active = False
        
        self.enemies = [e for e in self.enemies if e.hp > 0]
        
        # Verificar dano ao jogador
        for b in self.ebullets:
            if not b.active: continue
            if dist3(b.x, b.y, b.z, p.x, p.y, p.z) < 1.1:
                if p.take_damage(b.damage, self.sound_manager):
                    self.state = "GAME_OVER"
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)
                b.active = False
                self.shake = max(self.shake, 18)
        
        # Verificar conquistas
        self.achievements.check(self)
        self.achievements.update()
        
        # Próxima onda
        if len(self.enemies) == 0:
            self.wave += 1
            self.diff = 1 + self.wave * 0.22
            p.special_ammo = min(p.max_special, p.special_ammo+1)
            self.spawn_wave()
        
        # Timer de anúncio de onda
        if self.wave_announce_timer > 0:
            self.wave_announce_timer -= 1
        
        self.explosions = [ex for ex in self.explosions if ex.update()]

    def render_selection(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, -1, -18)
        
        draw_sky()
        draw_terrain()
        
        self.sel_preview_r = (self.sel_preview_r + 0.5) % 360
        
        for i, ac in enumerate(self.aircrafts):
            xpos = -8 + i*4.0
            glPushMatrix()
            glTranslatef(xpos, 1, 0)
            glRotatef(self.sel_preview_r, 0, 1, 0)
            ac.rx = ac.ry = ac.rz = 0
            if i == self.sel_idx:
                glScalef(1.2, 1.2, 1.2)
            ac.draw()
            glPopMatrix()
        
        W, H = DISPLAY
        spec = AIRCRAFT_SPECS[self.aircraft_names[self.sel_idx]]
        
        draw_text_centered("FORCA AEREA BRASILEIRA", W//2, H-30, FONT_LARGE, (255,220,60))
        draw_text_centered("SELECIONE SUA AERONAVE", W//2, H-70, FONT_MEDIUM, (255,255,255))
        
        for i, n in enumerate(self.aircraft_names):
            xp = 125 + i*207
            col = (80,220,255) if i==self.sel_idx else (160,160,160)
            draw_text_centered(f"[{i+1}] {n.split()[0]}", xp, H-160, FONT_SMALL, col)
        
        y = H - 200
        draw_text_centered(self.aircraft_names[self.sel_idx], W//2, y, FONT_MEDIUM, (80,220,255))
        draw_text_centered(spec["desc"], W//2, y-25, FONT_SMALL, (200,200,200))
        draw_text_2d(f"Vel: {spec['speed']} | Motor: {spec['engine']}", 10, y-50, FONT_TINY, (100,220,100))
        draw_text_2d(f"Man: {spec['maneuver']} | Peso: {spec['weight']}", 10, y-65, FONT_TINY, (100,180,255))
        draw_text_2d(f"Fogo: {spec['firepower']} | Especial: {spec['special']}", 10, y-80, FONT_TINY, (255,150,80))
        
        draw_text_centered("ENTER ou ESPACO para iniciar", W//2, 20, FONT_SMALL, (220,220,100))

    def render_game(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        p = self.player
        
        yr = math.radians(p.ry)
        cdist = 9 / self.zoom_level
        cheight = 3.0 / self.zoom_level
        
        tcx = p.x - math.sin(yr)*cdist + self.shake_x
        tcy = p.y + cheight + self.shake_y
        tcz = p.z + math.cos(yr)*cdist
        
        t = 0.12
        self.cam_x = lerp(self.cam_x, tcx, t)
        self.cam_y = lerp(self.cam_y, tcy, t)
        self.cam_z = lerp(self.cam_z, tcz, t)
        
        gluLookAt(self.cam_x, self.cam_y, self.cam_z,
                  p.x + math.sin(yr)*5, p.y, p.z - math.cos(yr)*5,
                  0, 1, 0)
        
        draw_sky()
        for c in self.clouds: c.draw()
        draw_terrain()
        
        p.draw(flash=p.hit_flash>0)
        for e in self.enemies: e.draw()
        for pu in self.powerups: pu.draw()
        for b in self.bullets + self.ebullets: b.draw()
        for ex in self.explosions: ex.draw()
        
        # HUD
        W, H = DISPLAY
        
        draw_crosshair(W//2, H//2, p.aiming)
        
        # Barras
        draw_bar_2d(12, H-28, 160, 14, p.health/p.max_health, (0.9,0.2,0.2))
        draw_text_2d(f"VIDA {p.health}/{p.max_health}", 178, H-30, FONT_SMALL, (255,100,100))
        
        draw_bar_2d(12, H-48, 160, 14, p.shield/p.max_shield, (0.1,0.6,1.0))
        draw_text_2d(f"ESCUDO {int(p.shield)}%", 178, H-50, FONT_SMALL, (80,190,255))
        
        draw_bar_2d(12, H-68, 160, 14, p.special_ammo/p.max_special, (1.0,0.55,0.0))
        draw_text_2d(f"{p.special_name}: {p.special_ammo}", 178, H-70, FONT_SMALL, (255,190,60))
        
        # Indicador de speed boost
        if p.speed_boost > 0:
            boost_ratio = p.speed_boost / 120
            draw_bar_2d(12, H-88, 160, 14, boost_ratio, (1, 1, 0))
            draw_text_2d(f"VELOCIDADE {boost_ratio*100:.0f}%", 178, H-90, FONT_SMALL, (255, 255, 0))
        
        # Info superior
        draw_text_2d(f"ONDA {self.wave}", W-150, H-30, FONT_MEDIUM, (255,255,255))
        draw_text_2d(f"PONTOS {p.score}", W-190, H-60, FONT_MEDIUM, (255,230,60))
        draw_text_2d(f"ABATES {p.kills}", W-165, H-90, FONT_MEDIUM, (255,180,80))
        
        # Mini-mapa
        self.draw_minimap()
        
        # Anúncio de onda
        if self.wave_announce_timer > 0:
            alpha = min(1, self.wave_announce_timer / 60)
            draw_text_centered(
                self.wave_announce_text,
                W//2, H//2 + 100,
                FONT_HUGE,
                (int(255*alpha), int(215*alpha), 0)
            )
        
        # Conquistas
        self.achievements.draw()
        
        # Controles
        draw_text_2d(f"{p.name} | {p.engine}", 12, H-105, FONT_SMALL, (160,200,255))
        draw_text_2d("W/S: Frente/Tras | A/D: Esq/Dir | Mouse: Mirar | B.Esq: Atirar | X: Especial | B.Dir: Zoom | P: Pausa", 
                     12, H-120, FONT_TINY, (140,140,140))
        
        if p.aiming:
            draw_text_centered(f"ZOOM {self.zoom_level:.1f}x", W//2, H-60, FONT_MEDIUM, (0,255,100))
        
        # Tela de pausa
        if self.state == "PAUSED":
            self.render_pause_screen()
        
        # Game Over
        if self.state == "GAME_OVER":
            self.render_game_over()
    
    def draw_minimap(self):
        """Mini-mapa no canto inferior direito"""
        mm_size = 100
        mm_x = DISPLAY[0] - mm_size - 10
        mm_y = 10
        scale = mm_size / 90  # Mapa cobre -45 a 45
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, DISPLAY[0], 0, DISPLAY[1])
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        
        # Fundo do mini-mapa
        glColor4f(0, 0, 0, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(mm_x - 2, mm_y - 2)
        glVertex2f(mm_x + mm_size + 2, mm_y - 2)
        glVertex2f(mm_x + mm_size + 2, mm_y + mm_size + 2)
        glVertex2f(mm_x - 2, mm_y + mm_size + 2)
        glEnd()
        
        # Borda
        glColor4f(0.3, 0.5, 0.3, 0.8)
        glBegin(GL_LINE_LOOP)
        glVertex2f(mm_x, mm_y)
        glVertex2f(mm_x + mm_size, mm_y)
        glVertex2f(mm_x + mm_size, mm_y + mm_size)
        glVertex2f(mm_x, mm_y + mm_size)
        glEnd()
        
        # Inimigos
        for e in self.enemies:
            ex = mm_x + (e.x + 45) * scale
            ey = mm_y + (e.z + 45) * scale
            glColor4f(1, 0, 0, 0.8)
            glPointSize(3)
            glBegin(GL_POINTS)
            glVertex2f(ex, ey)
            glEnd()
        
        # Power-ups
        for pu in self.powerups:
            px = mm_x + (pu.x + 45) * scale
            py = mm_y + (pu.z + 45) * scale
            glColor4f(*pu.TYPES[pu.type]['color'], 0.8)
            glPointSize(4)
            glBegin(GL_POINTS)
            glVertex2f(px, py)
            glEnd()
        
        # Jogador (triângulo)
        jx = mm_x + (self.player.x + 45) * scale
        jy = mm_y + (self.player.z + 45) * scale
        yr = math.radians(self.player.ry)
        glColor4f(0, 1, 0, 0.9)
        glBegin(GL_TRIANGLES)
        glVertex2f(jx + math.sin(yr) * 4, jy - math.cos(yr) * 4)
        glVertex2f(jx + math.sin(yr + 2.5) * 3, jy - math.cos(yr + 2.5) * 3)
        glVertex2f(jx + math.sin(yr - 2.5) * 3, jy - math.cos(yr - 2.5) * 3)
        glEnd()
        
        glDisable(GL_BLEND)
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
    
    def render_pause_screen(self):
        W, H = DISPLAY
        
        # Overlay escuro
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, W, 0, H)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glColor4f(0, 0, 0, 0.6)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(W, 0)
        glVertex2f(W, H)
        glVertex2f(0, H)
        glEnd()
        glDisable(GL_BLEND)
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        
        draw_text_centered("JOGO PAUSADO", W//2, H//2+40, FONT_HUGE, (255,255,255))
        draw_text_centered("Pressione P para continuar", W//2, H//2-10, FONT_MEDIUM, (200,200,200))
        draw_text_centered("ESC para menu principal", W//2, H//2-40, FONT_MEDIUM, (200,200,200))
    
    def render_game_over(self):
        W, H = DISPLAY
        
        # Overlay escuro
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, W, 0, H)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glColor4f(0, 0, 0, 0.7)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(W, 0)
        glVertex2f(W, H)
        glVertex2f(0, H)
        glEnd()
        glDisable(GL_BLEND)
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        
        draw_text_centered("AERONAVE ABATIDA", W//2, H//2+60, FONT_HUGE, (255,50,50))
        draw_text_centered(f"Pontuacao: {self.player.score}", W//2, H//2+20, FONT_LARGE, (255,230,60))
        draw_text_centered(f"Ondas: {self.wave-1} | Abates: {self.player.kills}", W//2, H//2-10, FONT_MEDIUM, (200,200,200))
        draw_text_centered("ESC ou ENTER para menu", W//2, H//2-50, FONT_MEDIUM, (160,160,160))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            self.handle_input()
            
            if self.state == "SELECTION":
                self.render_selection()
            elif self.state in ("PLAYING", "PAUSED", "GAME_OVER"):
                if self.state == "PLAYING":
                    self.update()
                self.render_game()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()