import tkinter as tk

from dc_tuner_studio import App


app = App()
app.after(1600, app.destroy)
app.mainloop()
print("GUI smoke test passed")
