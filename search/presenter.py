class Presenter(object):
    def __init__(self, model, view, interactor):
        self.Model = model
        self.View = view
        interactor.Install(self, view)
        self.View.Start()
