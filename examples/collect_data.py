import threading
import pygame
import sys
sys.path.append("..")
import rtde.rtde as rtde
import rtde.rtde_config as rtde_config
import rtde.csv_writer as csv_writer
import rtde.csv_binary_writer as csv_binary_writer
import tcp_client as tc
import datetime
import os

def record_robot(con, filename, frequency = 125, buffered = False, binary = False):
    global collecting_data

    writeModes = "wb" if binary else "w"
    with open(filename, writeModes) as csvfile:
        writer = None
        if binary:
            writer = csv_binary_writer.CSVBinaryWriter(csvfile, output_names, output_types)
        else:
            writer = csv_writer.CSVWriter(csvfile, output_names, output_types)

        writer.writeheader()

        i = 1
        while collecting_data:
            try:
                if buffered:
                    state = con.receive_buffered(binary)
                else:
                    state = con.receive(binary)
                if state is not None:
                    writer.writerow(state)
                    i += 1
            except KeyboardInterrupt:
                collecting_data = False

def control_gripper(con, watchdog):
    global collecting_data
    global setp

    while collecting_data:
            con.send(setp)
            # kick watchdog
            con.send(watchdog)


if __name__ == "__main__":
    DATE = str(datetime.date.today())
    FOLDER = os.path.join('C:/Users/xyao0/Desktop/project/data/assembly', DATE)
    if not os.path.isdir(FOLDER):
        os.mkdir(FOLDER)

    ### Setup config ####
    config = 'record_demo_configuration.xml'
    conf = rtde_config.ConfigFile(config)
    output_names, output_types = conf.get_recipe("state")
    setp_names, setp_types = conf.get_recipe("setp")
    watchdog_names, watchdog_types = conf.get_recipe("watchdog")

    ### Connect to the robot #######
    FREQUENCY = 125
    host = "169.254.139.87"
    port = 30004
    con = rtde.RTDE(host, port)
    con.connect()

    setp = con.send_input_setup(setp_names, setp_types)
    watchdog = con.send_input_setup(watchdog_names, watchdog_types)
    setp.input_bit_register_64 = True  #### Gripper open by default
    watchdog.input_int_register_0 = 0

    # get controller version
    con.get_controller_version()

    # setup recipes
    if not con.send_output_setup(output_names, output_types, frequency=FREQUENCY):
        print("Unable to configure output")
        sys.exit()

    # start data synchronization
    if not con.send_start():
        print("Unable to start synchronization")
        sys.exit()

    ### Connect to the camera ###
    my_camera = tc.command_camera()
    if my_camera.connected == 1:
        print("Camera connection success")
    else:
        print("Camera connection failure")

    ##### Set up pygame screen ##############
    n_trial = 0
    n_success = 0
    n_failure = 0
    pygame.init()
    size = [500, 700]
    WIN = pygame.display.set_mode(size)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    FPS = 20
    WIN.fill(WHITE)
    pygame.display.update()
    pygame.display.set_caption("Collect data")

    key_ring = {}
    Caps_lock = '1073741881'
    key_ring[Caps_lock] = 0  # 1073741881 is Caps lock. This value could change from keyboard to keyboard. This will be displayed in the screen  Caps lock = 1 + keys are the command set
    key_pressed = 0  # key press and release will happen one after another
    key_released = 0

    font1 = pygame.font.SysFont('aril', 26)
    font2 = pygame.font.SysFont('aril', 30)
    font3 = pygame.font.SysFont('aril', 150)
    text1 = font1.render('Caps Lock should be 1 to accept any of the keys', True, BLACK, WHITE)
    text3 = font1.render("Press 'c' to close the fingers", True, BLACK, WHITE)
    text4 = font1.render("Press 'o' to open the fingers", True, BLACK, WHITE)
    text5 = font1.render("Press 'b' to begin a trail", True, BLACK, WHITE)
    text6 = font1.render("Press 'f' for a failed trial", True, BLACK, WHITE)
    text7 = font1.render("Press 's' for a successful trail", True, BLACK, WHITE)
    text8 = font2.render("#Trial", True, BLACK, WHITE)
    text9 = font2.render("#Success", True, BLACK, WHITE)
    text10 = font2.render("#Failure", True, BLACK, WHITE)

    clock = pygame.time.Clock()
    run = True
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                key_pressed = event.key
                key_ring[str(key_pressed)] = 1
                if key_ring[Caps_lock] == 1:  # Caps lock is pressed
                    #######TODO: TALK TO THE ROBOT ########
                    if key_pressed == 98: ## Keyboard 'b'##
                        collecting_data = True
                        n_trial += 1
                        trial_id = str(datetime.datetime.now().timestamp()).split('.')[0]
                        filename = os.path.join(FOLDER , trial_id)
                        my_camera.start_trial(filename)
                        record_thread = threading.Thread(target=record_robot, args = [con, filename])
                        gripper_thread = threading.Thread(target=control_gripper, args = [con, watchdog])
                        record_thread.start()
                        gripper_thread.start()
                        print('Begin a trial')
                    elif key_pressed == 102 and collecting_data: #### Keyboard 'f' ####
                        print('Failure')
                        n_failure += 1
                        collecting_data = False
                        record_thread.join()
                        gripper_thread.join()
                        my_camera.stop_trial()
                    elif key_pressed == 115 and collecting_data: #### Keyboard 's' ####
                        print('Success')
                        collecting_data = False
                        record_thread.join()
                        gripper_thread.join()
                        n_success +=1
                        my_camera.stop_trial()
                    elif key_pressed == 111: #### Keyboard 'o' ####
                        print('Open the gripper')
                        setp.input_bit_register_64 = True  #### Gripper open
                    elif key_pressed == 99: #### Keyboard 'c' ####
                        setp.input_bit_register_64 = False ### Gripper close
                        print('Close the gripper')
            elif event.type == pygame.KEYUP:
                key_released = event.key
                key_ring[str(key_released)] = 0
            else:
                pass  # ignoring other non-logitech joystick event types
        WIN.blit(text1, (10, 20))
        text2 = font1.render(f'Caps Lock Key set to {key_ring[Caps_lock]}', True, BLACK, WHITE)
        text11 = font3.render(f"{n_trial}", True, RED, WHITE)
        text12 = font3.render(f"{n_success}", True, RED, WHITE)
        text13 = font3.render(f"{n_failure}", True, RED, WHITE)
        WIN.blit(text2, (10, 60))
        WIN.blit(text3, (10, 100))
        WIN.blit(text4, (10, 140))
        WIN.blit(text5, (10, 180))
        WIN.blit(text6, (10, 220))
        WIN.blit(text7, (10, 260))
        WIN.blit(text8, (10, 300))
        WIN.blit(text9, (10, 425))
        WIN.blit(text10, (10, 550))
        WIN.blit(text11, (250, 300))
        WIN.blit(text12, (250, 450))
        WIN.blit(text13, (250, 600))
        pygame.display.update()
    pygame.quit()

    # get controller version
    # con.get_controller_version()
    # t1 = threading.Thread(target = count)
    # t2 = threading.Thread(target = control_gripper)
    #
    # t1.start()
    # t2.start()
