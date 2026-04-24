"""
 * This is the source code of DanKertBSA, a bot for Brawl Stars on Android using ADB.
 * It is licensed under DanKert License.
 * You should have received a copy of the license in this archive (see LICENSE).
 * Author: DanKert, 2026.
 """
from time import time,sleep
from threading import Thread, Lock
from math import *
import numpy as np
import random
from constants import Constants
from modules.adb_input import ADBInput
"""
INITIALIZING: Initialize the bot
SEARCHING: Find the nearby bush to player
MOVING: Move to the selected bush
HIDING: Stop movement and hide in the bush
ATTACKING: Player will attack and activate gadget when enemy is nearby

"""
class BotState:
    INITIALIZING = 0
    SEARCHING = 1
    MOVING = 2
    HIDING = 3
    ATTACKING = 4

class Brawlbot:
    # In game tile width and height ratio with respect aspect ratio
    tile_w = 24
    tile_h = 17
    midpoint_offset = Constants.midpoint_offset

    # Map with sharp corners
    sharpCorner = Constants.sharpCorner
    # Either go to the closest bush to the player or the center
    centerOrder = Constants.centerOrder
    IGNORE_RADIUS = 0.5
    movement_screenshot = None
    screenshot = None
    INITIALIZING_SECONDS = 2
    results = []
    bushResult = []
    counter = 0
    direction = ["top","bottom","right","left"]
    current_bush = None
    last_player_pos = None
    last_closest_enemy = None
    border_size = 1
    stopped = True
    topleft = None
    avg_fps = 0
    enemy_move_key = None
    timeFactor = 1
    
    # time to move increase by 5% if maps have sharps corner
    if sharpCorner: timeFactor = 1.05

    def __init__(self,windowSize,offsets,speed,attack_range, adb_device_id=None) -> None:
        self.lock = Lock()
        self.adb_input = ADBInput(adb_device_id)
        
        # "brawler" chracteristic
        self.speed = speed
        # short range
        if attack_range >0 and attack_range <=4:
            range_multiplier = 1
            hide_multiplier = 1.3
        # medium range
        elif attack_range > 4 and attack_range <=7:
            range_multiplier = 0.85
            hide_multiplier = 1
        # long range
        elif attack_range > 7:
            range_multiplier = 0.8
            hide_multiplier = 0.8
        
        # attack range in tiles
        self.alert_range = attack_range + 2
        self.attack_range = range_multiplier*attack_range
        self.gadget_range = 0.9*self.attack_range
        self.hide_attack_range = 3.5 # visible to enemy in the bush
        self.HIDINGTIME = hide_multiplier * 23
        
        self.timestamp = time()
        self.window_w = windowSize[0]
        self.window_h = windowSize[1]
        self.center_window = (self.window_w / 2, int((self.window_h / 2)+ self.midpoint_offset))

        # Controls (support absolute pixels or relative 0..1)
        self.joystick_center = self._resolve_point(Constants.joystick_center)
        self.joystick_radius = self._resolve_length(Constants.joystick_radius)
        self.attack_button = self._resolve_point(getattr(Constants, "attack_button", (0.876, 0.74)))
        self.gadget_button = self._resolve_point(getattr(Constants, "gadget_button", (0.726, 0.556)))
        self.super_button = self._resolve_point(getattr(Constants, "super_button", (0.748, 0.787)))
        self.attack_taps = int(getattr(Constants, "attack_taps", 1))
        self.gadget_taps = int(getattr(Constants, "gadget_taps", 1))

        # tile size of the game
        # depended on the dimension of the game
        self.tileSize = round((round(self.window_w/self.tile_w)+round(self.window_h/self.tile_h))/2)
        self.state = BotState.INITIALIZING
        
        # offset
        self.offset_x = offsets[0]
        self.offset_y = offsets[1]

        #index
        self.player_index = 0
        self.bush_index = 1
        self.enemy_index = 2
        self.cube_index = 3

    def _resolve_point(self, point):
        """
        Resolve a point that can be either absolute pixels (x, y) or relative floats (0..1).
        """
        if not point or len(point) != 2:
            return (0, 0)
        x, y = point
        try:
            x_f, y_f = float(x), float(y)
        except Exception:
            return (int(x), int(y))
        if 0.0 <= x_f <= 1.0 and 0.0 <= y_f <= 1.0:
            return (round(x_f * self.window_w), round(y_f * self.window_h))
        return (round(x_f), round(y_f))

    def _resolve_length(self, value):
        """
        Resolve a length that can be absolute pixels (int) or relative float (0..1 of min(w, h)).
        """
        try:
            v = float(value)
        except Exception:
            return 0
        if 0.0 < v <= 1.0:
            return max(1, round(v * min(self.window_w, self.window_h)))
        return max(1, round(v))
        

    # translate a pixel position on a screenshot image to a pixel position on the screen.
    # pos = (x, y)
    # WARNING: if you move the window being captured after execution is started, this will
    # return incorrect coordinates, because the window position is only calculated in
    # the __init__ constructor.
    def get_screen_position(self, cordinate):
        """
        Apply screen offset
        :param cordinate (tuple): cordinate in the cropped screenshot
        :return: cordinate with offset applied
        """
        return (cordinate[0] + self.offset_x, cordinate[1] + self.offset_y)
    
    # storm method
    def guess_storm_direction(self):
        """
        Predict in game storm direction through the player position.

        eg. if player is off centre to the right guess the storm direction
        to be on the right.

        :return: (List) list of x and y direction or list of empty string
        """
        # asign x and y direction
        x_direction = ""
        y_direction =  ""
        # if there is a detection
        if self.results:
            # there player detection
            if self.results[self.player_index]:
                x_border = (self.window_w/self.tile_w)*self.border_size
                y_border = (self.window_h/self.tile_h)*self.border_size
                # coordinate of the middle of the screen
                p0 = self.center_window
                # coordinate of the player
                p1 = self.results[self.player_index][0]
                # get the difference between centre and the player
                xDiff , yDiff = tuple(np.subtract(p1, p0))
                # player is on the right
                if xDiff>x_border:
                    x_direction = self.direction[2]
                # player is on the left
                elif xDiff<-x_border:
                    x_direction = self.direction[3]
                # player is on the bottom
                if yDiff>y_border:
                    y_direction = self.direction[1]
                # player is on the top
                elif yDiff<-y_border:
                    y_direction = self.direction[0]
                return [x_direction,y_direction]
            else:
                return 2*[""]
        else:
            return 2*[""]
    
    def storm_movement_key(self):
        """
        get movement key to move away from the storm

        :return: (List) list of movement keys or an empty list
        """
        x = ""
        y = ""
        # if there is detection
        if self.results:
            # if there is player detection
            if self.results[self.player_index]:
                # predict the storm direction
                direction = self.guess_storm_direction()
                if direction[0] == self.direction[2]:
                    x = "a"
                # player is on the left
                elif direction[0] == self.direction[3]:
                    x = "d"
                # player is on the bottom
                if direction[1] == self.direction[1]:
                    y = "w"
                # player is on the top
                elif direction[1] == self.direction[0]:
                    y = "s"
        if [x,y] == ["",""]:
            return []
        else:
            return [x,y]

    def get_quadrant_bush(self):
        """
        get the quadrant to select a bush to move to.

        :return: False (boolean)
                 (List) list of "quadrants"
        """
        length = 0
        direction = self.guess_storm_direction()
        for i in range(len(direction)):
            if len(direction[i]) > 0:
                length += 1
                index = i
        if length == 0:
            return False
        elif length == 1:
            single_direction = direction[index]
            # top
            if single_direction == self.direction[0]:
                return [[0,3],[2,3]]
            # bottom
            elif single_direction == self.direction[1]:
                return [[0,3],[0,1]]
            # right
            elif single_direction == self.direction[2]:
                return [[0,1],[0,3]]
            # left
            elif single_direction == self.direction[3]:
                return [[2,3],[0,3]]
        elif length == 2:
            # top right
            if direction == [self.direction[0],self.direction[2]]:
                return [[0,2],[1,3]]
            # top left
            elif direction == [self.direction[0],self.direction[3]]:
                return [[1,3],[1,3]]
            # bottom right
            elif direction == [self.direction[1],self.direction[2]]:
                return [[0,2],[0,2]]
            # bottom left
            elif direction == [self.direction[1],self.direction[3]]:
                return [[1,3],[0,2]]
        
    # bush method
    def ordered_bush_by_distance(self, index):
        # our character is always in the center of the screen
        # if player position in result is empty
        # assume that player is in the middle of the screen
        if not(self.results[self.player_index]) or self.centerOrder:
            player_position = self.center_window
        else:
            player_position = self.results[self.player_index][0]
        def tile_distance(position):
            return sqrt(((position[0] - player_position[0])/(self.window_w/self.tile_w))**2 
                        + ((position[1] - player_position[1])/(self.window_h/self.tile_h))**2)
        # list of bush location is the in index 1 of results
        unfilteredResults = self.results[index]
        filteredResult = []
        # get quadrant
        quadrant = self.get_quadrant_bush()
        if quadrant:
            x_scale = self.window_w/3
            y_scale = self.window_h/3
            for x,y in unfilteredResults:
                # find bushes in the quadrant
                if ((x > quadrant[0][0]*x_scale and x <= quadrant[0][1]*x_scale)
                    and (y > quadrant[1][0]*y_scale and y <= quadrant[1][1]*y_scale)):
                    filteredResult.append((x,y))
            filteredResult.sort(key=tile_distance)
            if filteredResult:
                return filteredResult
        # if quadrant is False or filteredResult is empty
        if not(quadrant) or not(filteredResult):
            unfilteredResults.sort(key=tile_distance)
            return unfilteredResults
    
    def ordered_enemy_by_distance(self,index):
        # our character is always in the center of the screen
        # if player position in result is empty 
        # assume that player is in the middle of the screen
        if not(self.results[self.player_index]):
            player_position = self.center_window
        else:
            player_position = self.results[self.player_index][0]
        def tile_distance(position):
            return sqrt(((position[0] - player_position[0])/(self.window_w/self.tile_w))**2 
                        + ((position[1] - player_position[1])/(self.window_h/self.tile_h))**2)
        sortedResults = self.results[index]
        sortedResults.sort(key=tile_distance)
        return sortedResults
        
    def tile_distance(self,player_position,position):
        """
        get the tile distance between two coordinate

        :param player_position(tuple): position of the player
        :param position(tuple): coordinate of some position
        """
        return sqrt(((position[0] - player_position[0])/(self.window_w/self.tile_w))**2 + ((position[1] - player_position[1])/(self.window_h/self.tile_h))**2)
    
    def find_bush(self):
        """
        sort the bush by distance and assigned it to self.bushResult
        :return: True or False (boolean)
        """
        if self.results:
            self.bushResult = self.ordered_bush_by_distance(self.bush_index)
        if self.bushResult:
            return True
        else:
            return False
        
    def find_cube(self):
        """
        sort the cubes by distance and assigned it to self.cubeResult
        :return: True or False (boolean)
        """
        if self.results and self.results[self.cube_index]:
            self.cubeResult = self.ordered_enemy_by_distance(self.cube_index)
            return True
        return False

    def move_to_cube(self):
        """
        Move to the closest cube and attack it
        """
        if self.cubeResult:
            x, y = self.cubeResult[0]
            x, y = self.get_screen_position((x, y))
            self.adb_input.tap(x, y)
            self.attack()  # Attack the cube
            return True
        return False

    def move_to_bush(self):
        """
        Move towards the selected bush using joystick
        :return moveTime (float): The amount of time to move to the selected bush
        """
        if self.bushResult:
            x, y = self.bushResult[0]
            if not(self.results[self.player_index]):
                player_pos = self.center_window
            else:
                player_pos = self.results[self.player_index][0]
            
            # Calculate direction vector from player to bush
            dx = x - player_pos[0]
            dy = y - player_pos[1]
            distance = sqrt(dx*dx + dy*dy)
            
            if distance > 0:
                # Normalize direction
                dx /= distance
                dy /= distance
                
                # Calculate movement time based on tile distance
                tile_distance = self.tile_distance(player_pos, (x, y))
                move_time = tile_distance / self.speed * self.timeFactor
                
                print(f"Distance: {round(tile_distance, 2)} tiles")
                
                # Move in the calculated direction
                self.move_in_direction((dx, dy), move_time)
                
                return move_time
        return 0
    
    # enemy and attack method
    def attack(self):
        """
        Tap the attack button.
        """
        print("attacking enemy")
        for _ in range(max(1, self.attack_taps)):
            self.adb_input.tap(self.attack_button[0], self.attack_button[1])
            sleep(0.05)

    def gadget(self):
        """
        Tap the gadget button.
        """
        print("activate gadget")
        for _ in range(max(1, self.gadget_taps)):
            self.adb_input.tap(self.gadget_button[0], self.gadget_button[1])
            sleep(0.05)

    def move_in_direction(self, direction, duration):
        """
        Move in a specific direction using joystick simulation
        :param direction: Direction as (dx, dy) normalized vector
        :param duration: How long to hold the movement in seconds
        """
        dx, dy = direction
        # Calculate target position on joystick
        target_x = self.joystick_center[0] + dx * self.joystick_radius
        target_y = self.joystick_center[1] + dy * self.joystick_radius
        
        # Ensure target is within joystick bounds
        target_x = max(self.joystick_center[0] - self.joystick_radius, 
                      min(self.joystick_center[0] + self.joystick_radius, target_x))
        target_y = max(self.joystick_center[1] - self.joystick_radius,
                      min(self.joystick_center[1] + self.joystick_radius, target_y))

        # Hold joystick as a single continuous touch gesture.
        # Repeating short swipes causes "drop & re-grab" behavior in-game.
        duration_ms = max(100, int(duration * 1000))
        self.adb_input.swipe(
            self.joystick_center[0],
            self.joystick_center[1],
            target_x,
            target_y,
            duration=duration_ms,
        )

    def hold_movement_key(self, key, hold_time):
        """
        Hold down a movement key - now uses joystick simulation
        :param key (string): direction key ('w', 'a', 's', 'd')
        :param hold_time (float): time to hold the movement
        """
        # Convert key to direction vector
        direction_map = {
            'w': (0, -1),   # up
            's': (0, 1),    # down  
            'a': (-1, 0),   # left
            'd': (1, 0)     # right
        }
        if key in direction_map:
            direction = direction_map[key]
            self.move_in_direction(direction, hold_time)

    def storm_random_movement(self):
        """
        get movement keys and pick a random key to hold for one second
        """
        if self.storm_movement_key():
            move_keys = self.storm_movement_key()
        else:
            move_keys = ["w", "a", "s", "d"]
        random_move = random.choice(move_keys)
        hold_time = 1
        self.hold_movement_key(random_move,hold_time)
    
    def stuck_random_movement(self):
        """
        get movement keys and pick a random key to hold for one second
        """
        # If we have a direction from detections, use it. Otherwise move randomly.
        move_keys = self.get_movement_key(self.bush_index)
        if not move_keys:
            move_keys = [random.choice(["w", "a", "s", "d"])]
        # Hold movement via joystick simulation (ADB keyevents don't move the in-game joystick).
        for key in move_keys:
            self.hold_movement_key(key, 1)

    def get_movement_key(self,index):
        """
        get enemy direction
        :return:(List) List of x and y direction
        """
        # asign x and y direction
        x_key = ""
        y_key = ""
        if self.results:
            if self.results[self.player_index]:
                player_pos = self.results[self.player_index][0]
            # if player position in result is empty
            # assume that player is in the middle of the screen
            else:
                player_pos = self.center_window
            if self.results[index]:
                # enemy index
                if index == self.enemy_index:
                    p0 = self.enemyResults[0]
                elif index == self.bush_index:
                    p0 = self.bushResult[0]
                p1 = player_pos
                xDiff , yDiff = tuple(np.subtract(p1, p0))
                # right
                if xDiff>0:
                    x_key = "d"
                # left
                elif xDiff<0:
                    x_key = "a"
                # bottom
                if yDiff>0:
                    y_key = "s"
                # top
                elif yDiff<0:
                    y_key = "w"
                return [x_key,y_key]
        return []
    
    def enemy_random_movement(self):
        """
        Move player away from the enemy and attack
        """
        if not(self.enemy_move_key):
            move_keys = self.get_movement_key(self.enemy_index)
            if not(move_keys):
                move_keys = ["w", "a", "s", "d"]
                move_keys = random.choice(move_keys)
        else:
            move_keys = self.enemy_move_key
        # Move using joystick simulation (ADB keyevents don't control in-game joystick).
        keys = move_keys if isinstance(move_keys, list) else [move_keys]
        direction_map = {'w': (0, -1), 's': (0, 1), 'a': (-1, 0), 'd': (1, 0)}
        dx = dy = 0
        for key in keys:
            if key in direction_map:
                vx, vy = direction_map[key]
                dx += vx
                dy += vy
        length = sqrt(dx * dx + dy * dy)
        if length > 0:
            self.move_in_direction((dx / length, dy / length), 1)
        else:
            self.storm_random_movement()

        # Attack after repositioning
        self.attack()
        sleep(0.4)
        self.attack()

    def enemy_distance(self):
        """
        Calculate the enemy distance from the player
        """
        if self.results:
            # player coordinate
            if self.results[self.player_index]:
                player_pos = self.results[self.player_index][0]
            # if player position in result is empty
            # assume that player is in the middle of the screen
            else:
                player_pos = self.center_window
            # enemy coordinate
            if self.results[self.enemy_index]:
                self.enemyResults = self.ordered_enemy_by_distance(self.enemy_index)
                if self.enemyResults:
                    enemyDistance = self.tile_distance(player_pos,self.enemyResults[0])
                    # print(f"Closest enemy: {round(enemyDistance,2)} tiles")
                    return enemyDistance
        return None
    
    def is_enemy_in_range(self):
        """
        Check if enemy is in range of the player
        :return (boolean): True or False
        """
        enemyDistance = self.enemy_distance()
        if enemyDistance:
            # ranges in tiles
            if (enemyDistance > self.attack_range
                and enemyDistance <= self.alert_range):
                self.enemy_move_key = self.get_movement_key(self.enemy_index)
            elif (enemyDistance > self.gadget_range 
                  and enemyDistance <= self.attack_range):
                self.attack()
                return True
            elif enemyDistance <= self.gadget_range:
                self.gadget()
                self.attack()
                return True
        return False

    def is_enemy_close(self):
        """
        Check if enemy is visible in the bush
        :return (boolean): True or False
        """
        enemyDistance = self.enemy_distance()
        if enemyDistance:
            if enemyDistance <= self.hide_attack_range:
                self.gadget()
                self.attack()
                return True
        return False

    def is_player_damaged(self):
        """
        Check if player is damaged
        :return (boolean): True or False
        """
        if self.topleft and self.bottomright and self.screenshot is not None:
            width = abs(self.topleft[0] - self.bottomright[0])
            height = abs(self.topleft[1] - self.bottomright[1])
            w1 = int(self.topleft[0] + width/3)
            w2 = int(self.topleft[0] + 2*(width/3))
            h = int(self.topleft[1] - height/2)
            # Clamp within screenshot bounds
            h_img, w_img = self.screenshot.shape[:2]
            if 0 <= w1 < w_img and 0 <= h < h_img and 0 <= w2 < w_img:
                target_rgb = (204, 34, 34)
                tolerance = 20
                px1 = self.screenshot[h, w1]  # BGR
                px2 = self.screenshot[h, w2]  # BGR
                px1_rgb = (int(px1[2]), int(px1[1]), int(px1[0]))
                px2_rgb = (int(px2[2]), int(px2[1]), int(px2[0]))
                def close(rgb):
                    return all(abs(rgb[i] - target_rgb[i]) <= tolerance for i in range(3))
                if close(px1_rgb) or close(px2_rgb):
                    print("player is damaged")
                    return True
        return False
    
    def have_stopped_moving(self):
        """
        Check if player have stop moving
        :return (boolean): True or False
        """
        if self.results:
            if self.results[self.player_index]:
                player_pos = self.results[self.player_index][0]
                if self.last_player_pos is None:
                    self.last_player_pos = player_pos
                else:
                    # last player position is the same as the current
                    if self.last_player_pos == player_pos:
                        self.counter += 1
                        if self.counter == 2:
                            print("have stopped moving or stuck")
                            return True
                    else:
                        # reset counter
                        self.counter = 0
                    self.last_player_pos = player_pos
        return False

    def update_results(self,results):
        """
        update results from the detection
        """
        self.lock.acquire()
        self.results = results
        self.lock.release()
    
    def update_player(self,topleft,bottomright):
        """
        update player position for the is_player_damaged function
        """
        self.lock.acquire()
        self.topleft = topleft
        self.bottomright =bottomright
        self.lock.release()

    def update_screenshot(self, screenshot):
        """
        update screenshot
        """
        self.lock.acquire()
        self.screenshot = screenshot
        self.lock.release()

    def start(self):
        """
        start the bot
        """
        self.stopped = False
        self.loop_time = time()
        self.count = 0
        t = Thread(target=self.run)
        t.setDaemon(True)
        t.start()

    def stop(self):
        """
        stop the bot
        """
        self.stopped = True
        # reset last player position
        self.last_player_pos = None

    def run(self):
        while not self.stopped:
            sleep(0.01)
            if self.state == BotState.INITIALIZING:
                # do no bot actions until the startup waiting period is complete
                if time() > self.timestamp + self.INITIALIZING_SECONDS:
                    # start searching when the waiting period is over
                    self.lock.acquire()
                    self.state = BotState.SEARCHING
                    self.lock.release()

            elif self.state == BotState.SEARCHING:
                # Check for cubes first
                if self.find_cube():
                    print("Found cube, collecting")
                    self.move_to_cube()
                    sleep(1)  # Wait for collection
                success = self.find_bush()
                #if bush is detected
                if success:
                    print("found bush")
                    self.moveTime = self.move_to_bush()
                    self.lock.acquire()
                    self.timestamp = time()
                    self.state = BotState.MOVING
                    self.lock.release()
                #bush is not detected
                else:
                    print("Cannot find bush")
                    self.storm_random_movement()
                    # self.counter+=1
                
                if self.is_enemy_in_range():
                        self.lock.acquire()
                        self.state = BotState.ATTACKING
                        self.lock.release()

            elif self.state == BotState.MOVING:
                # when player is moving check if player is stuck
                if self.have_stopped_moving():
                    # cancel moving (no direct equivalent in ADB)
                    self.stuck_random_movement()
                    # and search for bush again
                    self.lock.acquire()
                    self.state = BotState.SEARCHING
                    self.lock.release()
                #if player is stuck
                else:
                    sleep(0.15)

                if self.is_enemy_in_range():
                    self.lock.acquire()
                    self.state = BotState.ATTACKING
                    self.lock.release()
                # player successfully travel to the selected bush
                if time() > self.timestamp + self.moveTime:
                    # Stop movement (no direct equivalent)
                    print("Hiding")
                    self.lock.acquire()
                    # change state to hiding
                    self.timestamp = time()
                    self.state = BotState.HIDING
                    self.lock.release()
                    
            elif self.state == BotState.HIDING:
                if time() > self.timestamp + self.HIDINGTIME or self.is_player_damaged():
                    print("Changing state to search")
                    self.lock.acquire()
                    self.state = BotState.SEARCHING
                    self.lock.release()

                if self.centerOrder:
                    if self.is_enemy_close():
                        print("Enemy is nearby")
                        self.lock.acquire()
                        self.state = BotState.ATTACKING
                        self.lock.release()
                else:
                    if self.is_enemy_in_range():
                        print("Enemy in range")
                        self.lock.acquire()
                        self.state = BotState.ATTACKING
                        self.lock.release()
            elif self.state == BotState.ATTACKING:
                if self.is_enemy_in_range():
                    self.enemy_random_movement()
                else:
                    self.lock.acquire()
                    self.state = BotState.SEARCHING
                    self.lock.release()
                    
            self.fps = (1 / (time() - self.loop_time))
            self.loop_time = time()
            self.count += 1
            if self.count == 1:
                self.avg_fps = self.fps
            else:
                self.avg_fps = (self.avg_fps*self.count+self.fps)/(self.count + 1)
