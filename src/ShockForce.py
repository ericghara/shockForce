import pandas as pd
from math import pi, tan, degrees
import matplotlib.animation as animation
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from IPython.display import HTML
import string
from os.path import join

class ShockForce:
    # Collection of methods to model static forces from shock compression
    def __init__(self, diameter=4.1, airgap=10.5, springRate=.87, preload=0):
        self.atmPres = 1.033  # kg/cm2 absolute
        self.P1 = self.atmPres  # kg/cm2 absolute
        self.P2 = None  # kg/cm2 absolute
        self.area = (diameter / 2) ** 2 * pi  # cm2
        self.airgap = airgap  # cm
        self.V1 = airgap * self.area  # cm**3
        self.V2 = None  # cm**3
        self.stroke = 0
        self.springRate = springRate  # kg/mm
        self.preload = preload  # cm
        self.gasForce = 0  # kg
        self.springForce = self.getSpringForce()  # kg; calculates preload force on init

    def getForces(self, stroke):
        self.stroke = stroke
        self.getSpringForce()
        self.getGasForce()
        return self.springForce, self.gasForce

    def getSpringForce(self):
        preloadForce = self.preload * self.springRate * 10 * 2  # multiply by 2 for both fork legs
        loadForce = self.stroke * self.springRate * 10 * 2
        self.springForce = preloadForce + loadForce
        return self.springForce  # kind of redundand to both set self.springForce and return it but makes funciton more versitile

    def getGasForce(self):
        self.V2 = self.V1 - (self.stroke * self.area)
        self.P2 = self.V1 / self.V2 * self.P1
        self.gasForce = (
                                    self.P2 - self.atmPres) * self.area * 2  # subtract atmPres to convert to gauge pressure; multiply by 2 for both fork legs
        return self.gasForce

    def forceSweep(self, E, B=0, step=.05):
        if E > self.airgap:
            print("***Error end stroke greater than airgap***")
        strokeIndex = []
        gasForce = []
        springForce = []
        combForce = []
        stroke = B
        while stroke <= E + .0001:  # adding .0001 to E to remove float representation inaccuracies
            spring, gas = self.getForces(stroke)
            strokeIndex.append(stroke);
            springForce.append(spring);
            gasForce.append(gas);
            combForce.append(spring + gas)
            stroke += step
        return {"Stroke": strokeIndex, "Combined Force": combForce, "Spring Force": springForce, "Gas Force": gasForce}


class Simulate:
    # Methods to visualize data from oldShockForce model
    def __init__(self):
        self.fig = None #matplotlib figure obj
        self.ax =  None #matplotlib axis objects
        self.ims = [] #List of artist object lists
        self.xmax = None # Max fork travel (used to set x axis)
        self.ymax = 800  # y axis max, set arbitrarily as y data tends towards infinity

    def get_data(self, simType="u", B=None, E=None, step=None, annotations=False):
        # If no args given then prompt user for simulation variables, otherwise run simulations using given variables
        simtType = simType.lower()  # remove case sensitivity
        funcDict = {
            "a" : self.airgapSweep,
            "p" : self.preloadSweep,
            "s" : self.springRateSweep
        }
        if simType in list(funcDict.keys()):
            data = funcDict[simType](B, E, step)
            #print("Processing. This may take a minute...") # Remove for Qt version
            self.dataAnimate(simType, data, annotations)
        elif simType == "u":
            simType = input("Select simulation Type: (a)irgap sweep, (p)reload sweep, (s)pring rate sweep (a,p,s) ")
            if simType == "a":
                B = float(input("Smallest airgap modeled (cm): (>0.0-10.5) "))
                E = float(input("Largest airgap modeled (cm): (0.0-10.5) "))
                step = float(input("Increment airgap increased by (cm): (0.05-0.50 recommended) "))
            elif simType == "p":
                B = float(input("Lowest preload modeled (cm): (0.0-10.5) "))
                E = float(input("Greatest preload modeled (cm): (0.0-10.5) "))
                step = float(input("Increment preload increased by (cm): (0.05-0.50 recommended) "))
            elif simType == "s":
                B = float(input("Softest spring rate modeled (cm): (0.0-1.3 recommended) "))
                E = float(input("Firmest spring rate modeled (cm): (0.0-1.3 recommended) "))
                step = float(input("Increment spring rate increased by (cm): (0.01-0.25 recommended) "))
            annotations = bool(input("Would you like annotations to be added? (0/1) "))
            return self.get_data(simType, B, E, step, annotations)
        else:
            print("Error: unrecognized simulation type (simType) selected")
            return False
        return self.fig, self.ims

    def saveAnimation(self, jsAnim):
        savePrompt = input(
            "Save model to disk, as HTML? (Select y if running outside of jupyter notebook) (y/n) ").lower()
        if savePrompt == "y":
            path = input("Path to save file: ")
            name = input("File name: ")
            if name[-5:].lower() != ".html":
                name += ".html"
            fullPath = join(path, name)
            try:
                with open(fullPath, "w") as f:
                    f.write(jsAnim)
                print("Save successful: %s " % fullPath)
            except:
                print("Error saving file at: %s" % fullPath)
                print("check save path and ensure you have permission to access destination folder.")
                self.saveAnimation(jsAnim)
        elif savePrompt == "n":
            pass
        else:
            self.saveAnimation(jsAnim)

    def airgapSweep(self, B, E, step=0.5):
        if B <= 0:
            print("Error increase beginning airgap. It is too small to model")
            return False
        df = []
        airgap = E
        while airgap >= B:
            fork = ShockForce(4.1, airgap, .87)
            dataDict = fork.forceSweep(airgap, 0, .01)
            plotDict = {"Spring Force": dataDict["Spring Force"], "Gas Force": dataDict["Gas Force"]}
            index = dataDict["Stroke"]
            df.append([airgap, pd.DataFrame(data=plotDict, index=index)])
            airgap -= step
        return df

    def preloadSweep(self, B, E, step=0.5):
        airgap = 10.5
        springRate = .87
        preload = E
        diameter = 4.1
        df = []
        if B < 0 or B >= airgap:
            print("Error preload must be start must be above 0 or and end below %s" % (airgap))
            return False
        while preload >= B:
            fork = ShockForce(diameter, airgap, springRate, preload)
            dataDict = fork.forceSweep(10.5, 0, .01)
            plotDict = {"Spring Force": dataDict["Spring Force"], "Gas Force": dataDict["Gas Force"]}
            index = dataDict["Stroke"]
            df.append([preload, pd.DataFrame(data=plotDict, index=index)])  # List of lists [preload,dataframe]
            preload -= step
        return df

    def springRateSweep(self, B, E, step=0.01):
        airgap = 10.5
        springRate = E
        preload = 0
        diameter = 4.1
        df = []
        if B < 0:
            print("Error - Spring Rate cannot be negative")
            return False
        while springRate >= B:
            fork = ShockForce(diameter, airgap, springRate, preload)
            dataDict = fork.forceSweep(10.5, 0, .01)
            plotDict = {"Spring Force": dataDict["Spring Force"], "Gas Force": dataDict["Gas Force"]}
            index = dataDict["Stroke"]
            df.append(
                [round(springRate, 2), pd.DataFrame(data=plotDict, index=index)])  # List of lists [preload,dataframe]
            springRate -= step
        return df

    def dataAnimateHelper(self, simType, key, df, annotations=True):
        #This is helper function returns lines and annotation artists specific to each simulation type
        ann = []  # List of annotations
        if simType == "a":
            title = "Air Gap: " + str(round(key, 1)) + " cm"  # need to round due to float representation error
            if annotations == True:
                ann.append(
                    self.ax.annotate('Max Fork Travel ', fontsize=19, xy=(round(df.index[-1], 2), self.ymax / 2), xycoords='data',
                                xytext=(int(self.xmax / 2), self.ymax * 7 / 8), textcoords='data',
                                arrowprops=dict(arrowstyle="simple, head_length=0.4,head_width=0.4, tail_width=0.1",
                                                shrinkA=15, shrinkB=0, facecolor="black"),
                                horizontalalignment='center', verticalalignment='top'))
        elif simType == "p":
            preloadForce = df['Spring Force'].min()  # Base preload force (ie spring force at 0cm compression)
            title = "Preload: " + str(round(key, 1)) + " cm"  # need to round due to float representation error
            if annotations == True:
                ann.append(self.ax.axline((df.index[0], preloadForce), (df.index[-1], preloadForce), color="black"))
                ann.append(self.ax.annotate(text='Preload Force', fontsize=19, xy=(self.xmax / 2, preloadForce), xycoords='data',
                                       xytext=(self.xmax / 2, self.ymax / 2), textcoords='data',
                                       arrowprops=dict(arrowstyle="simple, head_length=0.4,head_width=0.4, tail_width=0.1",
                                                       shrinkA=15, shrinkB=0, facecolor="black"),
                                       horizontalalignment='center', verticalalignment='top'))
        elif simType == "s":
            degrees_ = degrees(
                tan((df.iloc[300]["Spring Force"] - df.iloc[0]["Spring Force"]) / (df.index[300] - df.index[0]) * (
                        self.xmax / self.ymax)))  # the xmax/ymax normalizes with respect to x,y axis scales
            title = "Spring Rate: " + str(round(key + .001, 3))[
                                      :-1] + " kg/mm"  # need to round due to float representation error
            if annotations == True:
                line1, = self.ax.plot((df.index[0], df.index[300]),
                                 (df.iloc[0]["Spring Force"], df.iloc[300]["Spring Force"]),
                                 color="black")  # hypotenuse note format here is (x1,x2 vals), (y1, y2 vals), also see line2 comment
                ann.append(line1)
                line2, = self.ax.plot((df.index[0], df.index[300]),
                                 (df.iloc[0]["Spring Force"], df.iloc[0]["Spring Force"]),
                                 color="black")  # Base, comma after line2 trick to return single Line2D primitive instead of container list
                ann.append(line2)
                ann.append(
                    self.ax.annotate(text='', fontsize=19, xy=(df.index[300], df.iloc[300]["Spring Force"]), xycoords='data',
                                xytext=(df.index[300], df.iloc[0]["Spring Force"]), textcoords='data',
                                arrowprops=dict(arrowstyle="simple, head_length=0.3,head_width=0.3, tail_width=0.05",
                                                connectionstyle="arc3,rad=.3", shrinkA=0, shrinkB=0, facecolor="black"),
                                horizontalalignment='center', verticalalignment='top'))  # Curvy Arrow
                ann.append(self.ax.text(df.index[320], self.ymax*.03, str(round(degrees_)) + "°",
                                   fontsize=19, verticalalignment='center',
                                   horizontalalignment='left'))  # Text position fixed, but value is not, y pos is not.  Hence y pos set by first item in data list (greatest springrate)
        else:
            print('Error: dataAnimateHelper received an incorrect simType: "%s' % simType)
            return -1
        ann.append(self.ax.annotate(text=title, xy=(.99, .93), xycoords="axes fraction", verticalalignment='bottom',
                               horizontalalignment='right',
                               fontsize=17)) # Title annotation is something all animations share, placed outside of conditional statement chain
        return ann

    def dataAnimate(self,simType, data, annotations):
        self.xmax = 10.5 #not using data[0][1].index.max() for QtApp to avoid confusion from axis rescale  # Max fork travel (used to set x axis)
        self.fig, self.ax = plt.subplots()
        for key, df in data:
            im = plt.stackplot(df.index, df["Spring Force"], df["Gas Force"],
                               colors=("tab:blue", "tab:orange"), animated=True)  # returns list of 2 polycollections
            im.extend(self.dataAnimateHelper(simType, key, df, annotations))
            if key == data[0][0]:  # If we're at first frame, so do formatting setup
                labels = list(df.columns)
                self.legend = self.ax.legend(handles=im, labels=labels, loc='upper left', fontsize=15)
                self.ax.set(ylim=(0, self.ymax), xlim=(0, self.xmax))
                self.ax.set_xlabel("Fork Compression (cm)", fontsize=17)
                self.ax.set_ylabel("Force (kg)", fontsize=17)
                self.ax.tick_params(axis='x', labelsize=15)
                self.ax.tick_params(axis='y', labelsize=15)
                self.fig.set_size_inches(10.66, 6)
            self.ims.append(im)
        return True

