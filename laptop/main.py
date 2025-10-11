from GUI import GUI
from video_client import VideoClient

if __name__ == "__main__":
    
    animal_names = [
        "Cockatoo", "Crocodile", "Frog", "Kangaroo", "Koala", "Owl",
        "Platypus", "Snake", "Tasmanian Devil", "Wombat"
    ]

    
    hostIP = "raspberrypi.local"
    robotControlPort = 5000
    videoPort = 8000

    video_client = VideoClient(server_ip=hostIP, server_port=videoPort, animal_names=animal_names)

    app = GUI(host=hostIP, port=robotControlPort, camera=video_client)
    app.mainloop()

    video_client.stop()
    video_client.join()

