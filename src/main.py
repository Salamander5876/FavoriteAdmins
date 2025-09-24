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

# Частота кадров
FPS = 60
clock = pygame.time.Clock()

# Класс для машинки
class Car(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path):
        super().__init__()
        # Проверка наличия файла изображения
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл {image_path} не найден")
        self.original_image = pygame.image.load(image_path).convert_alpha()
        self.original_image = pygame.transform.scale(self.original_image, (37, 75))
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        
        self.speed = 0
        self.max_speed = 10
        self.acceleration = 0.15   # Увеличено для более отзывчивого управления
        self.deceleration = 0.15 / 10  # Увеличено для более плавного торможения
        self.angle = 0 
        self.rotation_speed = 5 / 2
    
    def update(self, keys, control_type):
        # Изменение скорости (ускорение и торможение)
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

        # Поворот (разрешён всегда)
        if control_type == "wasd":
            if keys[pygame.K_a]:
                self.angle += self.rotation_speed
            if keys[pygame.K_d]:
                self.angle -= self.rotation_speed
        elif control_type == "arrows":
            if keys[pygame.K_LEFT]:
                self.angle += self.rotation_speed
            if keys[pygame.K_RIGHT]:
                self.angle -= self.rotation_speed
        
        # Обновление положения на основе скорости и угла
        if abs(self.speed) > 0:  # Движение только при ненулевой скорости
            self.rect.x += self.speed * math.cos(math.radians(self.angle + 90))
            self.rect.y -= self.speed * math.sin(math.radians(self.angle + 90))

        # Вращение изображения
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        
        # Ограничение по экрану
        self.rect.clamp_ip(screen.get_rect())  # Упрощённое ограничение движения

# Главный игровой цикл
def game_loop():
    # Проверка наличия файла трассы
    track_path = "track.png"
    if not os.path.exists(track_path):
        raise FileNotFoundError(f"Файл {track_path} не найден")
    
    # Загружаем изображение трассы
    track_image = pygame.image.load(track_path).convert_alpha()
    track_image = pygame.transform.scale(track_image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    # Создание машинок
    try:
        car1 = Car(SCREEN_WIDTH // 8, SCREEN_HEIGHT // 2, "1.png")
        car2 = Car(SCREEN_WIDTH // 6, SCREEN_HEIGHT // 2, "9.png")
    except FileNotFoundError as e:
        print(e)
        pygame.quit()
        return

    all_sprites = pygame.sprite.Group()
    all_sprites.add(car1, car2)

    # Инициализация шрифта с поддержкой кириллицы
    try:
        font = pygame.font.SysFont("arial", 36)  # Arial обычно поддерживает кириллицу
    except:
        font = pygame.font.Font(None, 36)  # Запасной вариант

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        keys = pygame.key.get_pressed()
        
        # Обновляем положение машинок
        car1.update(keys, "wasd")
        car2.update(keys, "arrows")
        
        # Отрисовываем трассу на экране
        screen.blit(track_image, (0, 0))
        
        # Отрисовываем машинки
        all_sprites.draw(screen)

        # Отображение скорости первой машинки
        speed_text1 = f"Скорость 1: {car1.speed:.2f}"
        text_surface1 = font.render(speed_text1, True, BLACK)
        screen.blit(text_surface1, (10, 10))

        # Отображение скорости второй машинки
        speed_text2 = f"Скорость 2: {car2.speed:.2f}"
        text_surface2 = font.render(speed_text2, True, BLACK)
        screen.blit(text_surface2, (SCREEN_WIDTH - text_surface2.get_width() - 10, 10))
        
        pygame.display.flip()
        clock.tick(FPS)  # Ограничение FPS

    pygame.quit()

if __name__ == "__main__":
    try:
        game_loop()
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        pygame.quit()