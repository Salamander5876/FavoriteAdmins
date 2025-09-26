import pygame
import sys
import math
import os
import random
from PIL import Image
import io
import numpy as np

# Инициализация Pygame
pygame.init()
pygame.mixer.init()

# Константы
SCREEN_WIDTH, SCREEN_HEIGHT = 1800, 1000
FPS = 60

# Цвета
COLORS = {
    'WHITE': (255, 255, 255), 'BLACK': (0, 0, 0), 'RED': (255, 0, 0),
    'GREEN': (0, 255, 0), 'LIGHT_GRAY': (200, 200, 200), 
    'DARK_GRAY': (50, 50, 50), 'BLUE': (0, 100, 255), 'YELLOW': (255, 255, 0),
    'TRANSLUCENT': (0, 0, 0, 128), 'SHADOW': (20, 20, 20)
}

# Настройка дисплея и часов
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Гонки")
clock = pygame.time.Clock()

# Загрузка шрифта
try:
    font_path = os.path.join(os.path.dirname(__file__), "minecraft_0.ttf")
    fonts = {
        'large': pygame.font.Font(font_path, 18),
        'medium': pygame.font.Font(font_path, 12),
        'small': pygame.font.Font(font_path, 8)
    }
except:
    fonts = {
        'large': pygame.font.Font(None, 18),
        'medium': pygame.font.Font(None, 12),
        'small': pygame.font.Font(None, 8)
    }

# Кэш для изображений
image_cache = {}

def load_and_cache_image(image_path, size=None):
    if image_path not in image_cache:
        try:
            img = Image.open(image_path)
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            surface = pygame.image.load(buffer).convert_alpha()
            if size:
                surface = pygame.transform.scale(surface, size)
            image_cache[image_path] = surface
        except:
            surface = pygame.Surface(size or (25, 50)).convert_alpha()
            surface.fill(COLORS['RED'])
            image_cache[image_path] = surface
    return image_cache[image_path]

# Экран загрузки
def show_loading_screen():
    loading_text = fonts['large'].render("Подождите...", True, COLORS['WHITE'])
    loading_text_shadow = fonts['large'].render("Подождите...", True, COLORS['SHADOW'])
    start_time = pygame.time.get_ticks()
    
    while pygame.time.get_ticks() - start_time < 2000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        screen.fill(COLORS['DARK_GRAY'])
        screen.blit(loading_text_shadow, (SCREEN_WIDTH // 2 - loading_text.get_width() // 2 + 2, SCREEN_HEIGHT // 2 + 2))
        screen.blit(loading_text, (SCREEN_WIDTH // 2 - loading_text.get_width() // 2, SCREEN_HEIGHT // 2))
        
        pygame.display.flip()
        clock.tick(FPS)

# Загрузка текстур карты
def load_map_textures(tile_size):
    textures = {}
    for name, path in [
        ('grass', 'maps/grass.png'), ('asphalt', 'maps/asphalt.png'),
        ('finish', 'maps/finish.png'), ('wall', 'maps/wall.png')
    ]:
        textures[name] = load_and_cache_image(path, (tile_size, tile_size))
    return textures

# Поиск файлов машин и музыки
CAR_IMAGE_FOLDER = "cars"
AVAILABLE_CARS = sorted([
    f for f in os.listdir(CAR_IMAGE_FOLDER) 
    if f.lower().endswith(('.png', '.jpg', '.jpeg'))
]) if os.path.isdir(CAR_IMAGE_FOLDER) else ["1.png", "9.png", "24.png"]
CAR_PATHS = [os.path.join(CAR_IMAGE_FOLDER, car_file) for car_file in AVAILABLE_CARS]

MUSIC_FOLDER = "music"
AVAILABLE_MUSIC = sorted([
    f for f in os.listdir(MUSIC_FOLDER) 
    if f.lower().endswith('.mp3')
]) if os.path.isdir(MUSIC_FOLDER) else []
MUSIC_PATHS = [os.path.join(MUSIC_FOLDER, music_file) for music_file in AVAILABLE_MUSIC]

class Car(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, map_data, tile_size, player_id):
        super().__init__()
        self.original_image = load_and_cache_image(image_path, (20, 40))
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        
        self.player_id = player_id
        self.speed = 0
        self.max_speed = 12
        self.acceleration = 0.15
        self.deceleration = 0.015
        self.angle = 0
        self.rotation_speed = 2.5
        self.map_data = map_data
        self.tile_size = tile_size
        self.last_road_pos = (x, y)
        self.last_asphalt_pos = (x, y)
        self.laps = 0
        self.last_lap_time = 0
        self.control_type = ""
        self.joystick = None
        
        self.sin_angle = 0
        self.cos_angle = 1
        self.check_points = np.array([
            [12.5, -25], [12.5, 25], [-12.5, 25], [-12.5, -25]
        ])

    def get_points_to_check(self, x, y):
        angle_rad = math.radians(self.angle + 90)
        rot_matrix = np.array([
            [math.cos(angle_rad), -math.sin(angle_rad)],
            [math.sin(angle_rad), math.cos(angle_rad)]
        ])
        rotated_points = np.dot(self.check_points, rot_matrix)
        return rotated_points + np.array([x, y])

    def is_on_road(self, x, y):
        points = self.get_points_to_check(x, y)
        map_height, map_width = len(self.map_data), len(self.map_data[0])
        
        for px, py in points:
            map_x, map_y = int(px // self.tile_size), int(py // self.tile_size)
            if not (0 <= map_y < map_height and 0 <= map_x < map_width):
                return False, None
            tile = self.map_data[map_y][map_x]
            if tile not in ['0', '8', '2', '9']:
                return False, tile
        return True, tile

    def get_current_tile_type(self):
        map_x, map_y = int(self.rect.centerx // self.tile_size), int(self.rect.centery // self.tile_size)
        if 0 <= map_y < len(self.map_data) and 0 <= map_x < len(self.map_data[0]):
            return self.map_data[map_y][map_x]
        return None

    def update(self, keys, joystick, control_type):
        old_x, old_y = self.rect.center
        
        current_tile = self.get_current_tile_type()
        if current_tile in ['0', '8']:
            self.last_asphalt_pos = (old_x, old_y)
            max_speed = self.max_speed
            deceleration = self.deceleration
            rotation_speed = self.rotation_speed
        elif current_tile == '2':
            max_speed = 5
            deceleration = self.deceleration * 3
            rotation_speed = self.rotation_speed * 0.7
            self.speed = max(-5, min(self.speed, 5))
        else:
            max_speed = self.max_speed
            deceleration = self.deceleration
            rotation_speed = self.rotation_speed

        current_time = pygame.time.get_ticks()
        if current_tile == '9' and current_time - self.last_lap_time >= 3000:
            self.laps += 1
            self.last_lap_time = current_time

        if control_type == "wasd":
            if keys[pygame.K_w]:
                self.speed = min(self.speed + self.acceleration, max_speed)
            elif keys[pygame.K_s]:
                self.speed = max(self.speed - self.acceleration, -max_speed / 2)
            else:
                self.speed *= (1 - deceleration)
            
            if keys[pygame.K_a]:
                self.angle += rotation_speed
            if keys[pygame.K_d]:
                self.angle -= rotation_speed
            reset_pressed = keys[pygame.K_r]
        elif control_type == "arrows":
            if keys[pygame.K_UP]:
                self.speed = min(self.speed + self.acceleration, max_speed)
            elif keys[pygame.K_DOWN]:
                self.speed = max(self.speed - self.acceleration, -max_speed / 2)
            else:
                self.speed *= (1 - deceleration)
            
            if keys[pygame.K_LEFT]:
                self.angle += rotation_speed
            if keys[pygame.K_RIGHT]:
                self.angle -= rotation_speed
            reset_pressed = keys[pygame.K_RSHIFT]
        elif control_type == "xbox" and joystick:
            rt_input = (joystick.get_axis(5) + 1) / 2
            lt_input = (joystick.get_axis(4) + 1) / 2
            if rt_input > 0.1:
                self.speed = min(self.speed + self.acceleration * rt_input, max_speed)
            elif lt_input > 0.1:
                self.speed = max(self.speed - self.acceleration * lt_input, -max_speed / 2)
            else:
                self.speed *= (1 - deceleration)
                
            left_stick_x = joystick.get_axis(0)
            dpad_x = joystick.get_hat(0)[0]
            self.angle -= rotation_speed * (left_stick_x if abs(left_stick_x) > 0.1 else dpad_x)
            reset_pressed = joystick.get_button(2)
        else:
            reset_pressed = False

        if reset_pressed:
            self.rect.center = self.last_asphalt_pos
            self.speed = 0
            self.angle = 0

        self.angle %= 360
        angle_rad = math.radians(self.angle + 90)
        self.sin_angle = math.sin(angle_rad)
        self.cos_angle = math.cos(angle_rad)

        new_x = old_x + self.speed * self.cos_angle
        new_y = old_y - self.speed * self.sin_angle

        is_on_road, hit_tile = self.is_on_road(new_x, new_y)
        if is_on_road:
            self.rect.centerx = int(new_x)
            self.rect.centery = int(new_y)
            self.last_road_pos = (self.rect.centerx, self.last_road_pos[1])
            self.last_road_pos = (self.rect.centerx, self.rect.centery)
        else:
            self.rect.center = self.last_road_pos
            self.speed *= -0.5 if hit_tile == '1' else 0.5

        if abs(self.angle) > 0.01:
            self.image = pygame.transform.rotate(self.original_image, self.angle)
            self.rect = self.image.get_rect(center=self.rect.center)

        self.rect.clamp_ip(screen.get_rect())

def handle_collisions(cars):
    for i, car1 in enumerate(cars[:-1]):
        for car2 in cars[i+1:]:
            if car1.rect.colliderect(car2.rect):
                dx, dy = car1.rect.centerx - car2.rect.centerx, car1.rect.centery - car2.rect.centery
                distance = max(1, math.sqrt(dx*dx + dy*dy))
                min_distance = (car1.rect.width + car2.rect.width) * 0.6
                
                if distance < min_distance:
                    overlap = min_distance - distance
                    pushback = overlap / (distance * 2)
                    car1.rect.centerx += int(dx * pushback)
                    car1.rect.centery += int(dy * pushback)
                    car2.rect.centerx -= int(dx * pushback)
                    car2.rect.centery -= int(dy * pushback)
                    
                    relative_speed = car1.speed - car2.speed
                    car1.speed -= relative_speed * 0.7
                    car2.speed += relative_speed * 0.7
                    
                    if not car1.is_on_road(*car1.rect.center)[0]:
                        car1.rect.center = car1.last_road_pos
                        car1.speed *= -0.5
                    if not car2.is_on_road(*car2.rect.center)[0]:
                        car2.rect.center = car2.last_road_pos
                        car2.speed *= -0.5
                        
                    car1.speed = max(-car1.max_speed/2, min(car1.speed, car1.max_speed))
                    car2.speed = max(-car2.max_speed/2, min(car2.speed, car2.max_speed))

def load_map(filename):
    with open(filename, 'r') as file:
        return [list(line.strip()) for line in file]

def get_map_dimensions(map_data):
    return max(len(row) for row in map_data), len(map_data)

def get_spawn_points(map_data, tile_size):
    return [(x * tile_size + tile_size // 2, y * tile_size + tile_size // 2) 
            for y, row in enumerate(map_data) for x, tile in enumerate(row) if tile == '8']

def draw_text(surface, text, font, color, x, y, center=False, shadow=False):
    text_surface = font.render(text, True, color)
    if center:
        text_rect = text_surface.get_rect(center=(x, y))
    else:
        text_rect = text_surface.get_rect(topleft=(x, y))
    if shadow:
        shadow_surface = font.render(text, True, COLORS['SHADOW'])
        shadow_rect = shadow_surface.get_rect(topleft=(text_rect.x + 2, text_rect.y + 2))
        surface.blit(shadow_surface, shadow_rect)
    surface.blit(text_surface, text_rect)
    return text_rect

def draw_button(surface, rect, text, font, color, text_color, is_active, hover=False):
    bg_color = COLORS['YELLOW'] if hover else (COLORS['BLUE'] if is_active else color)
    pygame.draw.rect(surface, bg_color, rect, border_radius=12)
    pygame.draw.rect(surface, COLORS['WHITE'], rect, 2, border_radius=12)
    draw_text(surface, text, font, text_color, rect.centerx, rect.centery, True, True)

def main_menu():
    show_loading_screen()
    
    car_previews = {path: load_and_cache_image(path, (50, 100)) for path in CAR_PATHS}
    static_texts = {
        'title': fonts['large'].render("Настройка гонки", True, COLORS['WHITE']),
        'players': fonts['medium'].render("Игроки:", True, COLORS['WHITE']),
        'laps': fonts['medium'].render("Кругов для победы:", True, COLORS['WHITE']),
        'start': fonts['large'].render("Начать игру", True, COLORS['WHITE'])
    }

    joystick = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
    if joystick:
        joystick.init()

    player_settings = [
        {"car_index": 0, "control": "wasd", "active": True},
        {"car_index": 1 % len(CAR_PATHS), "control": "arrows", "active": False},
        {"car_index": 2 % len(CAR_PATHS), "control": "xbox", "active": False}
    ]
    num_players = 1
    laps_to_win = 3
    hover_states = {'start': False, 'players': [False] * 3, 'controls': [{} for _ in range(3)], 'cars': [False, False] * 3, 'laps': [False, False]}

    start_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, SCREEN_HEIGHT - 80, 180, 45)
    player_buttons_rects = [pygame.Rect(SCREEN_WIDTH // 2 - 90 + i * 60, 120, 50, 30) for i in range(3)]
    laps_controls_y = 160
    laps_prev_rect = pygame.Rect(SCREEN_WIDTH // 2 + 60, laps_controls_y, 30, 30)
    laps_next_rect = pygame.Rect(SCREEN_WIDTH // 2 + 100, laps_controls_y, 30, 30)

    menu_width = 1100
    player_row_height = 140
    menu_x = (SCREEN_WIDTH - menu_width) // 2
    setting_rows = [
        {
            "label_rect": pygame.Rect(menu_x + 25, 220 + i * player_row_height, 90, 30),
            "car_prev_rect": pygame.Rect(menu_x + 130, 220 + i * player_row_height, 50, 100),
            "prev_car_rect": pygame.Rect(menu_x + 100, 260 + i * player_row_height, 30, 30),
            "next_car_rect": pygame.Rect(menu_x + 190, 260 + i * player_row_height, 30, 30),
            "control_wasd_rect": pygame.Rect(menu_x + 260, 240 + i * player_row_height, 90, 30),
            "control_arrows_rect": pygame.Rect(menu_x + 360, 240 + i * player_row_height, 90, 30),
            "control_xbox_rect": pygame.Rect(menu_x + 460, 240 + i * player_row_height, 90, 30),
        } for i in range(3)
    ]

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        hover_states['start'] = start_button_rect.collidepoint(mouse_pos)
        for i, rect in enumerate(player_buttons_rects):
            hover_states['players'][i] = rect.collidepoint(mouse_pos)
        hover_states['laps'] = [laps_prev_rect.collidepoint(mouse_pos), laps_next_rect.collidepoint(mouse_pos)]
        for i, row in enumerate(setting_rows):
            hover_states['cars'][i*2] = row["prev_car_rect"].collidepoint(mouse_pos)
            hover_states['cars'][i*2+1] = row["next_car_rect"].collidepoint(mouse_pos)
            hover_states['controls'][i] = {
                'wasd': row["control_wasd_rect"].collidepoint(mouse_pos),
                'arrows': row["control_arrows_rect"].collidepoint(mouse_pos),
                'xbox': row["control_xbox_rect"].collidepoint(mouse_pos)
            }

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(player_buttons_rects):
                    if rect.collidepoint(mouse_pos):
                        num_players = i + 1
                        for j in range(3):
                            player_settings[j]["active"] = j < num_players
                        break
                            
                for i in range(num_players):
                    row = setting_rows[i]
                    if row["prev_car_rect"].collidepoint(mouse_pos):
                        player_settings[i]["car_index"] = (player_settings[i]["car_index"] - 1) % len(CAR_PATHS)
                    elif row["next_car_rect"].collidepoint(mouse_pos):
                        player_settings[i]["car_index"] = (player_settings[i]["car_index"] + 1) % len(CAR_PATHS)
                    elif row["control_wasd_rect"].collidepoint(mouse_pos):
                        player_settings[i]["control"] = "wasd"
                    elif row["control_arrows_rect"].collidepoint(mouse_pos):
                        player_settings[i]["control"] = "arrows"
                    elif row["control_xbox_rect"].collidepoint(mouse_pos) and joystick:
                        player_settings[i]["control"] = "xbox"
                
                if laps_prev_rect.collidepoint(mouse_pos):
                    laps_to_win = max(1, laps_to_win - 1)
                elif laps_next_rect.collidepoint(mouse_pos):
                    laps_to_win = min(99, laps_to_win + 1)
                                
                if start_button_rect.collidepoint(mouse_pos):
                    game_config = [
                        {
                            "car_path": CAR_PATHS[player_settings[i]["car_index"]],
                            "control": player_settings[i]["control"],
                            "joystick": joystick if player_settings[i]["control"] == "xbox" else None
                        } for i in range(num_players) if player_settings[i]["active"]
                    ]
                    controls_used = [config["control"] for config in game_config]
                    if any(controls_used.count(c) > 1 for c in set(controls_used)):
                        print("Управление не может быть назначено нескольким игрокам!")
                    else:
                        return game_config, laps_to_win

        screen.fill(COLORS['DARK_GRAY'])
        pygame.draw.rect(screen, (30, 30, 30, 200), (menu_x, 80, menu_width, SCREEN_HEIGHT - 160), border_radius=20)
        screen.blit(static_texts['title'], (SCREEN_WIDTH // 2 - static_texts['title'].get_width() // 2, 40))
        screen.blit(static_texts['players'], (SCREEN_WIDTH // 2 - 130, 120))
        
        for i, rect in enumerate(player_buttons_rects):
            draw_button(screen, rect, str(i + 1), fonts['medium'], COLORS['LIGHT_GRAY'], COLORS['WHITE'], i + 1 == num_players, hover_states['players'][i])
        
        screen.blit(static_texts['laps'], (SCREEN_WIDTH // 2 - 130, laps_controls_y))
        draw_button(screen, laps_prev_rect, "<", fonts['medium'], COLORS['LIGHT_GRAY'], COLORS['WHITE'], False, hover_states['laps'][0])
        draw_button(screen, laps_next_rect, ">", fonts['medium'], COLORS['LIGHT_GRAY'], COLORS['WHITE'], False, hover_states['laps'][1])
        draw_text(screen, str(laps_to_win), fonts['medium'], COLORS['WHITE'], SCREEN_WIDTH // 2 + 90, laps_controls_y + 15, True, True)

        for i, row in enumerate(setting_rows):
            is_active = player_settings[i]["active"]
            pygame.draw.rect(screen, (70, 70, 70, 200) if is_active else (30, 30, 30, 150), 
                           (menu_x + 10, row["label_rect"].y - 10, menu_width - 20, player_row_height - 5), border_radius=15)
            
            if not is_active:
                draw_text(screen, f"Игрок {i+1}: Выключен", fonts['medium'], (100, 100, 100), row["label_rect"].x, row["label_rect"].y, shadow=True)
                continue

            draw_text(screen, f"Игрок {i+1}:", fonts['medium'], COLORS['WHITE'], row["label_rect"].x, row["label_rect"].y, shadow=True)
            current_car_path = CAR_PATHS[player_settings[i]["car_index"]]
            car_rect = car_previews[current_car_path].get_rect(center=row["car_prev_rect"].center)
            pygame.draw.rect(screen, COLORS['BLACK'], car_rect.inflate(8, 8), border_radius=10)
            screen.blit(car_previews[current_car_path], car_rect)
            draw_button(screen, row["prev_car_rect"], "<", fonts['medium'], COLORS['LIGHT_GRAY'], COLORS['WHITE'], False, hover_states['cars'][i*2])
            draw_button(screen, row["next_car_rect"], ">", fonts['medium'], COLORS['LIGHT_GRAY'], COLORS['WHITE'], False, hover_states['cars'][i*2+1])
            draw_text(screen, "Управление:", fonts['medium'], COLORS['WHITE'], menu_x + 260, row["label_rect"].y, shadow=True)
            draw_button(screen, row["control_wasd_rect"], "WASD", fonts['medium'], COLORS['LIGHT_GRAY'], COLORS['WHITE'], 
                       player_settings[i]["control"] == "wasd", hover_states['controls'][i]['wasd'])
            draw_button(screen, row["control_arrows_rect"], "Стрелки", fonts['medium'], COLORS['LIGHT_GRAY'], COLORS['WHITE'], 
                       player_settings[i]["control"] == "arrows", hover_states['controls'][i]['arrows'])
            draw_button(screen, row["control_xbox_rect"], "Контроллер", fonts['medium'], COLORS['LIGHT_GRAY'], COLORS['WHITE'], 
                       player_settings[i]["control"] == "xbox", hover_states['controls'][i]['xbox'])
            if player_settings[i]["control"] == "xbox" and not joystick:
                draw_text(screen, "Нет джойстика!", fonts['small'], COLORS['RED'], row["control_xbox_rect"].x, row["control_xbox_rect"].y + 35, shadow=True)

        draw_button(screen, start_button_rect, "Начать игру", fonts['large'], COLORS['GREEN'], COLORS['WHITE'], True, hover_states['start'])
        pygame.display.flip()
        clock.tick(FPS)
        
    return [], 0

def victory_screen(winner_id, winner_control_type):
    show_loading_screen()
    
    text_surface = fonts['large'].render(f"ПОБЕДА! Игрок {winner_id} ({winner_control_type.upper()})", True, COLORS['YELLOW'])
    text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
    button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 60, 240, 45)
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        hover = button_rect.collidepoint(mouse_pos)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and button_rect.collidepoint(event.pos):
                return
        
        screen.fill(COLORS['DARK_GRAY'])
        pygame.draw.rect(screen, (30, 30, 30, 200), (SCREEN_WIDTH // 2 - 240, SCREEN_HEIGHT // 2 - 120, 480, 240), border_radius=20)
        screen.blit(text_surface, text_rect)
        draw_button(screen, button_rect, "Вернуться в меню", fonts['large'], COLORS['GREEN'], COLORS['WHITE'], True, hover)
        pygame.display.flip()
        clock.tick(FPS)

def game_loop(game_config, laps_to_win):
    show_loading_screen()
    
    map_data = load_map("maps/map1.txt")
    map_width, map_height = get_map_dimensions(map_data)
    tile_size = min(SCREEN_WIDTH // map_width, SCREEN_HEIGHT // map_height)
    textures = load_map_textures(tile_size)
    spawn_points = get_spawn_points(map_data, tile_size)
    
    if len(spawn_points) < len(game_config):
        raise ValueError(f"Недостаточно точек спавна (нужно минимум {len(game_config)})")
    
    cars = pygame.sprite.Group()
    for i, config in enumerate(game_config):
        car = Car(spawn_points[i][0], spawn_points[i][1], config["car_path"], map_data, tile_size, i + 1)
        car.control_type = config["control"]
        car.joystick = config["joystick"]
        cars.add(car)

    current_music = random.choice(MUSIC_PATHS) if MUSIC_PATHS else None
    music_name = os.path.splitext(os.path.basename(current_music))[0] if current_music else "Без музыки"
    if current_music:
        pygame.mixer.music.load(current_music)
        pygame.mixer.music.play(-1)
    
    music_text_surface = fonts['small'].render(f"Играет: {music_name}", True, COLORS['YELLOW'])
    music_text_x = SCREEN_WIDTH
    music_text_speed = -2
    
    hud_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    map_surface = pygame.Surface((map_width * tile_size, map_height * tile_size))
    for y, row in enumerate(map_data):
        for x, tile in enumerate(row):
            texture = textures.get(
                'asphalt' if tile in ['0', '8'] else 
                'finish' if tile == '9' else 
                'wall' if tile == '1' else 
                'grass'
            )
            map_surface.blit(texture, (x * tile_size, y * tile_size))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.mixer.music.stop()
                return
        
        keys = pygame.key.get_pressed()
        for car in cars:
            car.update(keys, car.joystick, car.control_type)
            if car.laps >= laps_to_win:
                pygame.mixer.music.stop()
                victory_screen(car.player_id, car.control_type)
                return

        handle_collisions(cars.sprites())
        
        screen.blit(map_surface, (0, 0))
        cars.draw(screen)

        hud_surface.fill((0, 0, 0, 0))
        for i, car in enumerate(cars):
            hud_rect = pygame.Rect(10 if i % 2 == 0 else SCREEN_WIDTH - 190, 10 + (i // 2) * 90, 180, 80)
            pygame.draw.rect(hud_surface, (30, 30, 30, 200), hud_rect, border_radius=15)
            pygame.draw.rect(hud_surface, COLORS['WHITE'], hud_rect, 2, border_radius=15)
            draw_text(hud_surface, f"P{car.player_id} ({car.control_type.upper()})", fonts['small'], COLORS['WHITE'], 
                     hud_rect.x + 8, hud_rect.y + 8, shadow=True)
            draw_text(hud_surface, f"Скорость: {car.speed:.2f}", fonts['small'], COLORS['RED'], 
                     hud_rect.x + 8, hud_rect.y + 30, shadow=True)
            draw_text(hud_surface, f"Круги: {car.laps}/{laps_to_win}", fonts['small'], COLORS['GREEN'], 
                     hud_rect.x + 8, hud_rect.y + 50, shadow=True)

        music_text_x += music_text_speed
        if music_text_x < -music_text_surface.get_width():
            music_text_x = SCREEN_WIDTH
        draw_text(hud_surface, f"Играет: {music_name}", fonts['small'], COLORS['YELLOW'], music_text_x, 15, shadow=True)

        screen.blit(hud_surface, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    try:
        while True:
            game_config, laps_to_win = main_menu()
            if game_config:
                game_loop(game_config, laps_to_win)
            else:
                break
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        pygame.mixer.music.stop()
        pygame.quit()