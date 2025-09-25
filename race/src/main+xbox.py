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

# Частота кадров
FPS = 60
clock = pygame.time.Clock()

# Класс для машинки
class Car(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, map_data, tile_size):
        super().__init__()
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл {image_path} не найден")
        self.original_image = pygame.image.load(image_path).convert_alpha()
        self.original_image = pygame.transform.scale(self.original_image, (37, 75))
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        
        self.speed = 0
        self.max_speed = 15
        self.acceleration = 0.15
        self.deceleration = 0.15 / 10
        self.angle = 0
        self.rotation_speed = 5 / 2
        self.map_data = map_data
        self.tile_size = tile_size
        self.last_road_pos = (x, y)
        self.original_max_speed = 15
        self.last_asphalt_pos = (x, y) # Новый атрибут для хранения последней позиции на асфальте

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
            if tile not in ['0', '8', '2']:
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
        
        # Обновляем последнюю позицию на асфальте, если мы на нём
        current_tile = self.get_current_tile_type()
        if current_tile == '0':
            self.last_asphalt_pos = (old_x, old_y)
        
        # Обновление максимальной скорости в зависимости от типа тайла
        if current_tile == '2':
            self.max_speed = 5
        else:
            self.max_speed = self.original_max_speed

        # Обработка управления
        if control_type == "wasd":
            if keys[pygame.K_w]:
                self.speed = min(self.speed + self.acceleration, self.max_speed)
            elif keys[pygame.K_s]:
                self.speed = max(self.speed - self.acceleration, -self.max_speed / 2)
            else:
                if self.speed > 0:
                    self.speed = max(self.speed - self.deceleration, 0)
                elif self.speed < 0:
                    self.speed = min(self.speed + self.deceleration, 0)
            
            if keys[pygame.K_a]:
                self.angle += self.rotation_speed
            if keys[pygame.K_d]:
                self.angle -= self.rotation_speed
            if keys[pygame.K_r]:
                self.rect.center = self.last_asphalt_pos
                self.speed = 0
        
        elif control_type == "arrows":
            if keys[pygame.K_UP]:
                self.speed = min(self.speed + self.acceleration, self.max_speed)
            elif keys[pygame.K_DOWN]:
                self.speed = max(self.speed - self.acceleration, -self.max_speed / 2)
            else:
                if self.speed > 0:
                    self.speed = max(self.speed - self.deceleration, 0)
                elif self.speed < 0:
                    self.speed = min(self.speed + self.deceleration, 0)
            
            if keys[pygame.K_LEFT]:
                self.angle += self.rotation_speed
            if keys[pygame.K_RIGHT]:
                self.angle -= self.rotation_speed
            if keys[pygame.K_RSHIFT]:
                self.rect.center = self.last_asphalt_pos
                self.speed = 0

        elif control_type == "xbox" and joystick:
            rt_axis = joystick.get_axis(5)
            lt_axis = joystick.get_axis(4)
            rt_input = (rt_axis + 1) / 2
            lt_input = (lt_axis + 1) / 2

            if rt_input > 0.1:
                self.speed = min(self.speed + self.acceleration * rt_input, self.max_speed)
            elif lt_input > 0.1:
                self.speed = max(self.speed - self.acceleration * lt_input, -self.max_speed / 2)
            else:
                if self.speed > 0:
                    self.speed = max(self.speed - self.deceleration, 0)
                elif self.speed < 0:
                    self.speed = min(self.speed + self.deceleration, 0)

            left_stick_x = joystick.get_axis(0)
            dpad_x, _ = joystick.get_hat(0)
            
            if abs(left_stick_x) > 0.1:
                self.angle -= self.rotation_speed * left_stick_x
            if dpad_x != 0:
                self.angle -= self.rotation_speed * dpad_x
            
            if joystick.get_button(2):
                self.rect.center = self.last_asphalt_pos
                self.speed = 0

        # Вычисляем новую позицию
        new_x = old_x + self.speed * math.cos(math.radians(self.angle + 90))
        new_y = old_y - self.speed * math.sin(math.radians(self.angle + 90))

        # Проверка столкновения с травой
        if self.is_on_road(new_x, new_y):
            self.rect.centerx = int(new_x)
            self.rect.centery = int(new_y)
            self.last_road_pos = (self.rect.centerx, self.rect.centery)
        else:
            self.rect.center = self.last_road_pos
            self.speed = -self.speed * 0.5

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
    width = max(len(row) for row in map_data)  # Ширина — максимальная длина строки
    height = len(map_data)  # Высота — количество строк
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
            if pygame.sprite.collide_rect(car1, car2):
                dx = car1.rect.centerx - car2.rect.centerx
                dy = car1.rect.centery - car2.rect.centery
                distance = max(1, math.sqrt(dx**2 + dy**2))
                
                pushback_x = dx / distance
                pushback_y = dy / distance
                
                car1.rect.centerx += int(pushback_x)
                car1.rect.centery += int(pushback_y)
                car2.rect.centerx -= int(pushback_x)
                car2.rect.centery -= int(pushback_y)
                
                car1.speed = -car1.speed * 0.5
                car2.speed = -car2.speed * 0.5

# Главный игровой цикл
def game_loop():
    map_path = "maps/map1.txt"
    if not os.path.exists(map_path):
        raise FileNotFoundError(f"Файл {map_path} не найден")
    
    map_data = load_map(map_path)
    width, height = get_map_dimensions(map_data)
    tile_size = min(SCREEN_WIDTH // width, SCREEN_HEIGHT // height)  # Масштабируем по меньшему измерению

    spawn_points = get_spawn_points(map_data)

    if len(spawn_points) < 3:
        raise ValueError("Недостаточно точек спавна (нужно минимум 3)")

    if not (os.path.exists("maps/grass.png") and os.path.exists("maps/asphalt.png")):
        raise FileNotFoundError("Файлы grass.png или asphalt.png не найдены в папке maps")
    grass_texture = pygame.image.load("maps/grass.png").convert()
    asphalt_texture = pygame.image.load("maps/asphalt.png").convert()
    grass_texture = pygame.transform.scale(grass_texture, (tile_size, tile_size))
    asphalt_texture = pygame.transform.scale(asphalt_texture, (tile_size, tile_size))

    joystick_count = pygame.joystick.get_count()
    if joystick_count > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"Обнаружен джойстик: {joystick.get_name()}")
    else:
        joystick = None
        print("Джойстик не обнаружен. Третья машинка будет без управления.")

    try:
        car1 = Car(spawn_points[0][0] * tile_size + tile_size // 2, spawn_points[0][1] * tile_size + tile_size // 2, "1.png", map_data, tile_size)
        car2 = Car(spawn_points[1][0] * tile_size + tile_size // 2, spawn_points[1][1] * tile_size + tile_size // 2, "9.png", map_data, tile_size)
        car3 = Car(spawn_points[2][0] * tile_size + tile_size // 2, spawn_points[2][1] * tile_size + tile_size // 2, "24.png", map_data, tile_size)
    except FileNotFoundError as e:
        print(e)
        pygame.quit()
        return

    all_sprites = pygame.sprite.Group()
    all_sprites.add(car1, car2, car3)
    cars = [car1, car2, car3]

    try:
        font = pygame.font.SysFont("arial", 36)
    except:
        font = pygame.font.Font(None, 36)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        keys = pygame.key.get_pressed()
        
        car1.update(keys, None, "wasd")
        car2.update(keys, None, "arrows")
        car3.update(keys, joystick, "xbox")

        handle_collisions(cars)
        
        for y, row in enumerate(map_data):
            for x, tile in enumerate(row):
                if tile in ['0', '8']:
                    screen.blit(asphalt_texture, (x * tile_size, y * tile_size))
                else:
                    screen.blit(grass_texture, (x * tile_size, y * tile_size))
        
        all_sprites.draw(screen)

        speed_text1 = f"Скорость (WASD): {car1.speed:.2f}"
        text_surface1 = font.render(speed_text1, True, RED)
        screen.blit(text_surface1, (10, 10))

        speed_text2 = f"Скорость (Стрелки): {car2.speed:.2f}"
        text_surface2 = font.render(speed_text2, True, RED)
        screen.blit(text_surface2, (SCREEN_WIDTH - text_surface2.get_width() - 10, 10))

        speed_text3 = f"Скорость (XBOX): {car3.speed:.2f}"
        text_surface3 = font.render(speed_text3, True, RED)
        screen.blit(text_surface3, (10, 50))
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    try:
        game_loop()
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        pygame.quit()