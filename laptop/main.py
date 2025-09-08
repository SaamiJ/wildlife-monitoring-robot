from GUI import GUI
from video_client import VideoClient

if __name__ == "__main__":
    
    animal_names = ["Wombat", "Kookaburra", "Lizard", "Koala", "Kangaroo", "Platypus",
                "Frog", "Crocodile", "Cockatoo", "Dingo", "Bat", "Snake", "Emu",
                "Possum", "Wallaby"]
    
    hostIP = 'raspberrypi.local'
    robotControlPort = 5000
    videoPort = 8000

    video_client = VideoClient(server_ip='raspberrypi.local', server_port=8000,animal_names=animal_names)
    video_client.start()

    app = GUI(host=hostIP, port=robotControlPort, camera=0)
    app.mainloop()

    video_client.stop()
    video_client.join()

