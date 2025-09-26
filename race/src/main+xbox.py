import pygame
import sys
import math
import os

# Инициализация Pygame
pygame.init()

# Настройки окна
SCREEN_WIDTH = 1800
SCREEN_HEIGHT = 1000
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Гонки")

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
BLUE = (0, 100, 255)
YELLOW = (255, 255, 0)

# Частота кадров
FPS = 60
clock = pygame.time.Clock()

# Поиск всех файлов машин в папке 'cars'
CAR_IMAGE_FOLDER = "cars"
AVAILABLE_CARS = []
if os.path.isdir(CAR_IMAGE_FOLDER):
    AVAILABLE_CARS = sorted([f for f in os.listdir(CAR_IMAGE_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
else:
    # Запасной вариант, если папка 'cars' не найдена
    AVAILABLE_CARS = ["1.png", "9.png", "24.png"]
    print(f"Внимание: Папка '{CAR_IMAGE_FOLDER}' не найдена. Используются запасные имена файлов.")

# Если нет доступных машин, используем заглушку
if not AVAILABLE_CARS:
    AVAILABLE_CARS = ["placeholder.png"]
    print("Внимание: В папке 'cars' не найдено изображений. Используется заглушка.")
# Для использования в классе Car, пути должны быть полными
CAR_PATHS = [os.path.join(CAR_IMAGE_FOLDER, car_file) for car_file in AVAILABLE_CARS]

# Класс для машинки
class Car(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, map_data, tile_size, player_id):
        super().__init__()
        # Игнорируем проверку, если это заглушка
        if not os.path.exists(image_path) and image_path != "placeholder.png":
            # Создаем красную прямоугольную заглушку, если файл не найден
            self.original_image = pygame.Surface((37, 75)).convert_alpha()
            self.original_image.fill(RED)
        else:
            self.original_image = pygame.image.load(image_path).convert_alpha()
            self.original_image = pygame.transform.scale(self.original_image, (37, 75))
            
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        
        self.player_id = player_id # Добавляем ID игрока
        self.speed = 0
        self.max_speed = 10
        self.acceleration = 0.15
        self.deceleration = 0.15 / 10
        self.angle = 0
        self.rotation_speed = 6 / 2
        self.map_data = map_data
        self.tile_size = tile_size
        self.last_road_pos = (x, y)
        self.original_max_speed = 10
        self.last_asphalt_pos = (x, y)
        self.laps = 0  # Счётчик кругов
        self.last_lap_time = 0  # Время последнего засчитанного круга (в миллисекундах)
        self.control_type = ""
        self.joystick = None

    def get_points_to_check(self, x, y):
        """Возвращает список точек для проверки столкновений."""
        points = []
        half_width = self.rect.width / 2
        half_height = self.rect.height / 2
        
        angle_rad = math.radians(self.angle + 90)
        
        points.append((x + half_width * math.cos(angle_rad) - half_height * math.sin(angle_rad), y - half_width * math.sin(angle_rad) - half_height * math.cos(angle_rad)))
        points.append((x + half_width * math.cos(angle_rad) + half_height * math.sin(angle_rad), y - half_width * math.sin(angle_rad) + half_height * math.cos(angle_rad)))
        points.append((x - half_width * math.cos(angle_rad) + half_height * math.sin(angle_rad), y + half_width * math.sin(angle_rad) + half_height * math.cos(angle_rad)))
        points.append((x - half_width * math.cos(angle_rad) - half_height * math.sin(angle_rad), y + half_width * math.sin(angle_rad) - half_height * math.cos(angle_rad)))
        
        return points

    def is_on_road(self, x, y):
        """Проверяет, находятся ли все ключевые точки машинки на дороге."""
        points = self.get_points_to_check(x, y)
        for px, py in points:
            map_x, map_y = int(px / self.tile_size), int(py / self.tile_size)
            if not (0 <= map_y < len(self.map_data) and 0 <= map_x < len(self.map_data[0])):
                return False
            tile = self.map_data[map_y][map_x]
            if tile not in ['0', '8', '2', '9']:  # Разрешено движение по '9' (финиш)
                return False
        return True

    def get_current_tile_type(self):
        """Возвращает тип тайла, на котором находится центр машинки."""
        map_x, map_y = int(self.rect.centerx / self.tile_size), int(self.rect.centery / self.tile_size)
        if 0 <= map_y < len(self.map_data) and 0 <= map_x < len(self.map_data[0]):
            return self.map_data[map_y][map_x]
        return None

    def update(self, keys, joystick, control_type):
        old_x, old_y = self.rect.centerx, self.rect.centery
        
        current_tile = self.get_current_tile_type()
        if current_tile == '0' or current_tile == '8': # Асфальт и спавн
            self.last_asphalt_pos = (old_x, old_y)
        
        # Обновление максимальной скорости и трения в зависимости от типа тайла
        if current_tile == '2':  # Трава
            self.max_speed = 5
            effective_deceleration = self.deceleration * 3  # Увеличенное трение на траве
            effective_rotation_speed = self.rotation_speed * 0.7  # Меньшая маневренность на траве
        else:
            self.max_speed = self.original_max_speed
            effective_deceleration = self.deceleration
            effective_rotation_speed = self.rotation_speed

        # Проверка на пересечение финишной линии (плитка '9')
        current_time = pygame.time.get_ticks() 
        if current_tile == '9' and current_time - self.last_lap_time >= 3000:  # Прошло 3 секунды с прошлого круга
            self.laps += 1
            self.last_lap_time = current_time 

        # --- Обработка управления ---
        forward_input = 0
        reverse_input = 0
        turn_input = 0
        reset_pressed = False

        if control_type == "wasd":
            if keys[pygame.K_w]:
                forward_input = 1
            if keys[pygame.K_s]:
                reverse_input = 1
            if keys[pygame.K_a]:
                turn_input = 1
            if keys[pygame.K_d]:
                turn_input = -1
            if keys[pygame.K_r]:
                reset_pressed = True
        
        elif control_type == "arrows":
            if keys[pygame.K_UP]:
                forward_input = 1
            if keys[pygame.K_DOWN]:
                reverse_input = 1
            if keys[pygame.K_LEFT]:
                turn_input = 1
            if keys[pygame.K_RIGHT]:
                turn_input = -1
            if keys[pygame.K_RSHIFT]:
                reset_pressed = True

        elif control_type == "xbox" and joystick:
            rt_axis = joystick.get_axis(5)
            lt_axis = joystick.get_axis(4)
            forward_input = (rt_axis + 1) / 2
            reverse_input = (lt_axis + 1) / 2
            
            left_stick_x = joystick.get_axis(0)
            dpad_x, _ = joystick.get_hat(0)
            
            if abs(left_stick_x) > 0.1:
                turn_input = -left_stick_x
            elif dpad_x != 0:
                turn_input = -dpad_x

            if joystick.get_button(2): # Кнопка X
                reset_pressed = True

        # Ускорение/Торможение (сглаженное)
        if forward_input > 0.1:
            self.speed += self.acceleration * forward_input
            self.speed = min(self.speed, self.max_speed)
        elif reverse_input > 0.1:
            self.speed -= self.acceleration * reverse_input
            self.speed = max(self.speed, -self.max_speed / 2)
        else:
            # Накат/Торможение с учетом поверхности
            if self.speed > 0:
                self.speed = max(self.speed - effective_deceleration, 0)
            elif self.speed < 0:
                self.speed = min(self.speed + effective_deceleration, 0)
        
        # Поворот (с учетом поверхности)
        if abs(self.speed) > 0.1 and abs(turn_input) > 0.1:
            # Чем выше скорость, тем меньше радиус поворота
            effective_rotation = effective_rotation_speed * turn_input * (1 - abs(self.speed) / self.max_speed * 0.5)
            self.angle += effective_rotation
        
        # Сброс
        if reset_pressed:
            self.rect.center = self.last_asphalt_pos
            self.speed = 0

        # Вычисляем новую позицию
        new_x = old_x + self.speed * math.cos(math.radians(self.angle + 90))
        new_y = old_y - self.speed * math.sin(math.radians(self.angle + 90))

        # Проверка столкновения с границами
        if self.is_on_road(new_x, new_y):
            self.rect.centerx = int(new_x)
            self.rect.centery = int(new_y)
            self.last_road_pos = (self.rect.centerx, self.rect.centery)
        else:
            # Не обновляем позицию, чтобы не заходить в блоки
            # Скорость не меняем - она продолжит изменяться от ввода
            # Это позволит ехать назад, если новая позиция назад будет допустимой
            self.rect.centerx = self.last_road_pos[0]
            self.rect.centery = self.last_road_pos[1]

        # Вращение изображения
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        
        self.rect.clamp_ip(screen.get_rect())

# Функция загрузки карты и определения спавн-поинтов
def load_map(filename):
    with open(filename, 'r') as file:
        map_data = [list(line.strip()) for line in file]
    return map_data

def get_map_dimensions(map_data):
    """Возвращает ширину и высоту карты."""
    width = max(len(row) for row in map_data)
    height = len(map_data)
    return width, height

def get_spawn_points(map_data):
    spawn_points = []
    for y, row in enumerate(map_data):
        for x, tile in enumerate(row):
            if tile == '8':
                spawn_points.append((x, y))
    return spawn_points

# Функция для обработки столкновений между машинами
def handle_collisions(cars):
    for i in range(len(cars)):
        for j in range(i + 1, len(cars)):
            car1 = cars[i]
            car2 = cars[j]
            
            collision_count = 0
            while pygame.sprite.collide_rect(car1, car2) and collision_count < 10:  # Цикл для полного разрешения столкновения
                # Векторы от центра одной машины к другой
                dx = car1.rect.centerx - car2.rect.centerx
                dy = car1.rect.centery - car2.rect.centery
                distance = max(1, math.sqrt(dx**2 + dy**2))  # Избегаем деления на 0
                
                # Вычисляем минимальное расстояние, необходимое для разделения
                # Сумма половин ширины и высоты прямоугольников машин (усиленный запас)
                min_distance = (car1.rect.width + car2.rect.width) / 2 * 1.2  # Увеличен запас до 20%
                
                # Если расстояние меньше минимального, разделяем машины
                if distance < min_distance:
                    # Нормализованный вектор направления
                    pushback_x = dx / distance
                    pushback_y = dy / distance
                    
                    # Вычисляем величину смещения для каждой машины
                    overlap = min_distance - distance
                    correction_x = pushback_x * overlap / 2
                    correction_y = pushback_y * overlap / 2
                    
                    # Перемещаем машины
                    car1.rect.centerx += int(correction_x)
                    car1.rect.centery += int(correction_y)
                    car2.rect.centerx -= int(correction_x)
                    car2.rect.centery -= int(correction_y)
                    
                    # Проверка, что машины находятся на дороге после разделения
                    if not car1.is_on_road(car1.rect.centerx, car1.rect.centery):
                        car1.rect.center = car1.last_road_pos
                    if not car2.is_on_road(car2.rect.centerx, car2.rect.centery):
                        car2.rect.center = car2.last_road_pos
                    
                    # Уменьшение скорости с учетом направления (усиленная потеря)
                    relative_speed = car1.speed - car2.speed
                    speed_reduction = 0.8  # Увеличенная потеря скорости
                    car1.speed -= relative_speed * speed_reduction * 0.5
                    car2.speed += relative_speed * speed_reduction * 0.5
                    
                    # Ограничение скорости
                    car1.speed = max(-car1.max_speed / 2, min(car1.speed, car1.max_speed))
                    car2.speed = max(-car2.max_speed / 2, min(car2.speed, car2.max_speed))
                
                collision_count += 1

# --- Функции меню и UI ---

def get_car_preview(car_path):
    """Загружает и масштабирует изображение машины для меню."""
    if not os.path.exists(car_path):
        preview = pygame.Surface((74, 150))
        preview.fill(RED)
    else:
        original_image = pygame.image.load(car_path).convert_alpha()
        preview = pygame.transform.scale(original_image, (74, 150))
    return preview

def draw_text(surface, text, font, color, x, y):
    """Вспомогательная функция для отрисовки текста."""
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, (x, y))
    return text_surface.get_rect(topleft=(x, y))

def draw_button(surface, rect, text, font, color, text_color, is_active):
    """Вспомогательная функция для отрисовки кнопки."""
    bg_color = BLUE if is_active else color
    pygame.draw.rect(surface, bg_color, rect, border_radius=10)
    pygame.draw.rect(surface, WHITE, rect, 2, border_radius=10)
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=rect.center)
    surface.blit(text_surface, text_rect)

# --- Главное меню ---

def main_menu():
    """Отображает меню выбора машины, управления, количества игроков и кругов."""
    try:
        font_large = pygame.font.SysFont("arial", 48, bold=True)
        font_medium = pygame.font.SysFont("arial", 36)
        font_small = pygame.font.SysFont("arial", 24)
    except:
        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 24)

    # Инициализация джойстика
    joystick_count = pygame.joystick.get_count()
    joystick = None
    if joystick_count > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()

    # Настройки по умолчанию
    max_players = 3
    player_settings = [
        {"car_index": 0, "control": "wasd", "active": True},
        {"car_index": 1 % len(CAR_PATHS) if CAR_PATHS else 0, "control": "arrows", "active": False},
        {"car_index": 2 % len(CAR_PATHS) if CAR_PATHS else 0, "control": "xbox", "active": False}
    ]
    num_players = 1
    laps_to_win = 3 # Начальное количество кругов
    
    # Кнопка "Начать игру"
    start_button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - 100, 300, 60)
    
    # Выбор количества игроков
    player_buttons_rects = [
        pygame.Rect(SCREEN_WIDTH // 2 - 150 + i * 100, 150, 80, 40) for i in range(max_players)
    ]

    # Выбор количества кругов
    laps_controls_y = 210
    laps_prev_rect = pygame.Rect(SCREEN_WIDTH // 2 + 100, laps_controls_y, 40, 40)
    laps_next_rect = pygame.Rect(SCREEN_WIDTH // 2 + 250, laps_controls_y, 40, 40)
    laps_display_rect = pygame.Rect(SCREEN_WIDTH // 2 + 150, laps_controls_y, 90, 40)


    # Размеры и позиции элементов меню
    menu_width = 1500
    player_row_height = 200
    menu_x = (SCREEN_WIDTH - menu_width) // 2
    
    setting_rows = []
    for i in range(max_players):
        row_y = 280 + i * player_row_height # Сдвигаем ниже, чтобы освободить место для выбора кругов
        setting_rows.append({
            "label_rect": pygame.Rect(menu_x + 50, row_y, 150, 40),
            "car_prev_rect": pygame.Rect(menu_x + 220, row_y, 74, 150),
            "prev_car_rect": pygame.Rect(menu_x + 160, row_y + 60, 40, 40),
            "next_car_rect": pygame.Rect(menu_x + 310, row_y + 60, 40, 40),
            "car_name_rect": pygame.Rect(menu_x + 200, row_y + 155, 150, 30),
            "control_wasd_rect": pygame.Rect(menu_x + 400, row_y + 40, 150, 40),
            "control_arrows_rect": pygame.Rect(menu_x + 570, row_y + 40, 150, 40),
            "control_xbox_rect": pygame.Rect(menu_x + 740, row_y + 40, 150, 40),
        })


    running = True
    while running:
        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Левая кнопка мыши
                    mouse_pos = event.pos
                    
                    # Обработка кнопок количества игроков
                    for i in range(max_players):
                        if player_buttons_rects[i].collidepoint(mouse_pos):
                            num_players = i + 1
                            for j in range(max_players):
                                player_settings[j]["active"] = (j < num_players)
                            break
                            
                    # Обработка кнопок выбора кругов
                    if laps_prev_rect.collidepoint(mouse_pos):
                        laps_to_win = max(1, laps_to_win - 1)
                    elif laps_next_rect.collidepoint(mouse_pos):
                        laps_to_win = min(10, laps_to_win + 1)
                    
                    # Обработка кнопок настроек игроков
                    for i in range(num_players):
                        # Выбор машины
                        if setting_rows[i]["prev_car_rect"].collidepoint(mouse_pos):
                            player_settings[i]["car_index"] = (player_settings[i]["car_index"] - 1) % len(CAR_PATHS)
                        elif setting_rows[i]["next_car_rect"].collidepoint(mouse_pos):
                            player_settings[i]["car_index"] = (player_settings[i]["car_index"] + 1) % len(CAR_PATHS)

                        # Выбор управления
                        if setting_rows[i]["control_wasd_rect"].collidepoint(mouse_pos):
                            player_settings[i]["control"] = "wasd"
                        elif setting_rows[i]["control_arrows_rect"].collidepoint(mouse_pos):
                            player_settings[i]["control"] = "arrows"
                        elif setting_rows[i]["control_xbox_rect"].collidepoint(mouse_pos):
                            if joystick:
                                player_settings[i]["control"] = "xbox"
                            else:
                                print("Джойстик не подключен!")
                                
                    # Кнопка "Начать игру"
                    if start_button_rect.collidepoint(mouse_pos):
                        # Собираем данные для запуска игры
                        game_config = []
                        for i in range(num_players):
                            config = {
                                "car_path": CAR_PATHS[player_settings[i]["car_index"]],
                                "control": player_settings[i]["control"],
                                "joystick": joystick if player_settings[i]["control"] == "xbox" and i < joystick_count else None 
                            }
                            game_config.append(config)
                            
                        # Проверяем уникальность управления
                        controls_used = [config["control"] for config in game_config]
                        if controls_used.count("wasd") > 1 or controls_used.count("arrows") > 1 or controls_used.count("xbox") > 1:
                            print("Внимание: Управление WASD, Стрелки и XBOX (джойстик) может быть назначено только ОДНОМУ игроку!")
                        else:
                            return game_config, laps_to_win
        
        # Отрисовка
        screen.fill(DARK_GRAY)
        
        # Заголовок
        draw_text(screen, "Настройка гонки", font_large, WHITE, SCREEN_WIDTH // 2 - 150, 50)
        
        # Выбор количества игроков
        draw_text(screen, "Игроки:", font_medium, WHITE, SCREEN_WIDTH // 2 - 250, 150)
        for i in range(max_players):
            is_selected = (i + 1 == num_players)
            draw_button(screen, player_buttons_rects[i], str(i + 1), font_medium, LIGHT_GRAY, BLACK, is_selected)
        
        # Выбор количества кругов
        draw_text(screen, "Кругов для победы:", font_medium, WHITE, SCREEN_WIDTH // 2 - 250, laps_controls_y)
        draw_button(screen, laps_prev_rect, "<", font_medium, LIGHT_GRAY, BLACK, False)
        draw_button(screen, laps_next_rect, ">", font_medium, LIGHT_GRAY, BLACK, False)
        pygame.draw.rect(screen, WHITE, laps_display_rect, border_radius=5)
        draw_text(screen, str(laps_to_win), font_medium, BLACK, laps_display_rect.centerx - font_medium.size(str(laps_to_win))[0] // 2, laps_controls_y + 5)


        # Настройки игроков
        for i in range(max_players):
            row = setting_rows[i]
            is_active = player_settings[i]["active"]
            
            # Фон строки
            row_bg_color = (70, 70, 70) if is_active else (30, 30, 30)
            pygame.draw.rect(screen, row_bg_color, (menu_x, row.get("label_rect").y - 20, menu_width, player_row_height - 10), border_radius=10)
            
            if not is_active:
                draw_text(screen, f"Игрок {i+1}: Выключен", font_medium, (100, 100, 100), row.get("label_rect").x, row.get("label_rect").y)
                continue

            draw_text(screen, f"Игрок {i+1}:", font_medium, WHITE, row.get("label_rect").x, row.get("label_rect").y)
            
            # Выбор машины
            current_car_path = CAR_PATHS[player_settings[i]["car_index"]]
            car_preview = get_car_preview(current_car_path)
            screen.blit(car_preview, row["car_prev_rect"].topleft)
            
            # Имя файла машины
            car_file_name = os.path.basename(current_car_path)
            draw_text(screen, car_file_name, font_small, WHITE, row["car_name_rect"].centerx - font_small.size(car_file_name)[0] // 2, row["car_name_rect"].y)

            # Кнопки < > для смены машины
            draw_button(screen, row["prev_car_rect"], "<", font_medium, LIGHT_GRAY, BLACK, False)
            draw_button(screen, row["next_car_rect"], ">", font_medium, LIGHT_GRAY, BLACK, False)
            
            # Выбор управления
            control = player_settings[i]["control"]
            draw_text(screen, "Управление:", font_medium, WHITE, menu_x + 400, row.get("label_rect").y)
            draw_button(screen, row["control_wasd_rect"], "WASD", font_medium, LIGHT_GRAY, BLACK, control == "wasd")
            draw_button(screen, row["control_arrows_rect"], "Стрелки", font_medium, LIGHT_GRAY, BLACK, control == "arrows")
            draw_button(screen, row["control_xbox_rect"], "Контроллер", font_medium, LIGHT_GRAY, BLACK, control == "xbox")
            
            if control == "xbox" and not joystick:
                 draw_text(screen, "Нет джойстика!", font_small, RED, row["control_xbox_rect"].x, row["control_xbox_rect"].y + 50)


        # Кнопка "Начать игру"
        draw_button(screen, start_button_rect, "Начать игру", font_large, GREEN, WHITE, True)
        
        pygame.display.flip()
        clock.tick(FPS)
        
    return [], 0 

# --- Экран победы ---

def victory_screen(winner_id, winner_control_type):
    """Отображает экран победителя."""
    try:
        font_giant = pygame.font.SysFont("arial", 96, bold=True)
        font_large = pygame.font.SysFont("arial", 48)
    except:
        font_giant = pygame.font.Font(None, 96)
        font_large = pygame.font.Font(None, 48)

    message = f"ПОБЕДА! Игрок {winner_id} ({winner_control_type.upper()})"
    text_surface = font_giant.render(message, True, YELLOW)
    text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))

    button_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 + 100, 400, 70)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    return # Возвращаемся в main_menu
        
        screen.fill(BLACK)
        screen.blit(text_surface, text_rect)
        
        draw_button(screen, button_rect, "Вернуться в меню", font_large, GREEN, WHITE, True)
        
        pygame.display.flip()
        clock.tick(FPS)


# --- Главный игровой цикл ---

def game_loop(game_config, laps_to_win):
    map_path = "maps/map1.txt"
    if not os.path.exists(map_path):
        raise FileNotFoundError(f"Файл {map_path} не найден")
    
    map_data = load_map(map_path)
    width, height = get_map_dimensions(map_data)
    tile_size = min(SCREEN_WIDTH // width, SCREEN_HEIGHT // height)

    spawn_points = get_spawn_points(map_data)
    if len(spawn_points) < len(game_config):
        raise ValueError(f"Недостаточно точек спавна (нужно минимум {len(game_config)})")

    # Проверка наличия текстур
    required_textures = ["maps/grass.png", "maps/asphalt.png", "maps/finish.png", "maps/wall.png"]
    for texture in required_textures:
        if not os.path.exists(texture):
            print(f"Внимание: Файл {texture} не найден. Используется заглушка.")
    
    # Загрузка и масштабирование текстур
    try:
        grass_texture = pygame.image.load("maps/grass.png").convert()
        asphalt_texture = pygame.image.load("maps/asphalt.png").convert()
        finish_texture = pygame.image.load("maps/finish.png").convert()
        wall_texture = pygame.image.load("maps/wall.png").convert()
    except:
        # Заглушки, если файлы не найдены
        grass_texture = pygame.Surface((tile_size, tile_size)); grass_texture.fill((0, 150, 0))
        asphalt_texture = pygame.Surface((tile_size, tile_size)); asphalt_texture.fill((80, 80, 80))
        finish_texture = pygame.Surface((tile_size, tile_size)); finish_texture.fill((150, 150, 150))
        wall_texture = pygame.Surface((tile_size, tile_size)); wall_texture.fill((100, 100, 100))
        
    grass_texture = pygame.transform.scale(grass_texture, (tile_size, tile_size))
    asphalt_texture = pygame.transform.scale(asphalt_texture, (tile_size, tile_size))
    finish_texture = pygame.transform.scale(finish_texture, (tile_size, tile_size))
    wall_texture = pygame.transform.scale(wall_texture, (tile_size, tile_size))

    cars = []
    all_sprites = pygame.sprite.Group()
    
    # Создание машин на основе конфигурации из меню
    for i, config in enumerate(game_config):
        car = Car(
            spawn_points[i][0] * tile_size + tile_size // 2, 
            spawn_points[i][1] * tile_size + tile_size // 2, 
            config["car_path"], 
            map_data, 
            tile_size,
            i + 1 # ID игрока (1, 2, 3...)
        )
        car.control_type = config["control"]
        car.joystick = config["joystick"]
        cars.append(car)
        all_sprites.add(car)

    try:
        font = pygame.font.SysFont("arial", 36)
    except:
        font = pygame.font.Font(None, 36)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return # Выход из игры
        
        keys = pygame.key.get_pressed()
        
        # Обновление всех машин
        winner = None
        for car in cars:
            car.update(keys, car.joystick, car.control_type)
            # Проверка условия победы
            if car.laps >= laps_to_win:
                winner = car
                break
        
        if winner:
            victory_screen(winner.player_id, winner.control_type)
            return # Возвращаемся в main_menu

        handle_collisions(cars)
        
        # Очистка экрана перед отрисовкой (фикс наложения текста)
        screen.fill(BLACK)  # Или другой цвет фона, например DARK_GRAY, если нужно
        
        # Отрисовка карты
        for y, row in enumerate(map_data):
            for x, tile in enumerate(row):
                if tile in ['0', '8']:
                    screen.blit(asphalt_texture, (x * tile_size, y * tile_size))
                elif tile == '9':
                    screen.blit(finish_texture, (x * tile_size, y * tile_size))
                elif tile == '1':
                    screen.blit(wall_texture, (x * tile_size, y * tile_size))
                elif tile == '2':
                    screen.blit(grass_texture, (x * tile_size, y * tile_size))
                else:
                    screen.blit(grass_texture, (x * tile_size, y * tile_size))
        
        all_sprites.draw(screen)

        # Отображение информации (Улучшенное расположение)
        for i, car in enumerate(cars):
            # Левая сторона - Скорость
            speed_text = f"P{car.player_id} ({car.control_type.upper()}): {car.speed:.2f}"
            text_surface_speed = font.render(speed_text, True, RED)
            screen.blit(text_surface_speed, (10, 10 + i * 40))

            # Правая сторона - Круги
            laps_text = f"Круги: {car.laps} / {laps_to_win}"
            laps_surface = font.render(laps_text, True, GREEN)
            screen.blit(laps_surface, (SCREEN_WIDTH - laps_surface.get_width() - 10, 10 + i * 40))
        
        pygame.display.flip()
        clock.tick(FPS)

# --- Запуск игры ---

if __name__ == "__main__":
    try:
        while True:
            # 1. Вызываем меню и ждем конфигурацию и количество кругов
            result = main_menu()
            game_config, laps_to_win = result

            # 2. Если конфигурация получена, запускаем игру
            if game_config:
                game_loop(game_config, laps_to_win)
            else:
                # Если main_menu вернуло пустой список, значит, выходим
                break

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        pygame.quit()
        sys.exit()

    pygame.quit()