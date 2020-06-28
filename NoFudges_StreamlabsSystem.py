# -*- coding: utf-8 -*-

#---------------------------
#   Import Libraries
#---------------------------
import clr, codecs, json, os, re, sys, threading, datetime

clr.AddReference("IronPython.Modules.dll")
clr.AddReferenceToFileAndPath(os.path.join(os.path.dirname(os.path.realpath(__file__)) + "\References", r"TwitchLib.PubSub.dll"))
from TwitchLib.PubSub import TwitchPubSub

#---------------------------
#   [Required] Script Information
#---------------------------
ScriptName = "No Fudges Given Channel Point Reward"
Website = "https://www.twitch.tv/EncryptedThoughts"
Description = "Script for a channel point reward to start a countdown overlay for how long not to give a fudge."
Creator = "EncryptedThoughts"
Version = "1.0.0.0"

#---------------------------
#   Define Global Variables
#---------------------------
SettingsFile = os.path.join(os.path.dirname(__file__), "settings.json")
RefreshTokenFile = os.path.join(os.path.dirname(__file__), "tokens.json")
ReadMe = os.path.join(os.path.dirname(__file__), "README.txt")
EventReceiver = None
ThreadQueue = []
CurrentThread = None
PlayNextAt = datetime.datetime.now()
TokenExpiration = None
LastTokenCheck = None # Used to make sure the bot doesn't spam trying to reconnect if there's a problem
RefreshToken = None
AccessToken = None
UserID = None

InvalidRefreshToken = False

#---------------------------------------
# Classes
#---------------------------------------
class Settings(object):
    def __init__(self, SettingsFile=None):
        if SettingsFile and os.path.isfile(SettingsFile):
            with codecs.open(SettingsFile, encoding="utf-8-sig", mode="r") as f:
                self.__dict__ = json.load(f, encoding="utf-8")
        else:
            self.EnableDebug = False
            self.TwitchAuthCode = ""
            self.TwitchRewardName = ""
            self.TwitchRewardActivationType = "Immediate"
            self.TimerLength = 60
            self.ResetCommand = "!FuckUp"
            self.RedeemedSFXPath = ""
            self.RedeemedSFXVolume = 100
            self.RedeemedSFXDelay = 10
            self.FinishedSFXPath = ""
            self.FinishedSFXVolume = 100

    def Reload(self, jsondata):
        self.__dict__ = json.loads(jsondata, encoding="utf-8")
        return

    def Save(self, SettingsFile):
        try:
            with codecs.open(SettingsFile, encoding="utf-8-sig", mode="w+") as f:
                json.dump(self.__dict__, f, encoding="utf-8")
            with codecs.open(SettingsFile.replace("json", "js"), encoding="utf-8-sig", mode="w+") as f:
                f.write("var settings = {0};".format(json.dumps(self.__dict__, encoding='utf-8')))
        except:
            Parent.Log(ScriptName, "Failed to save settings to file.")
        return

#---------------------------
#   [Required] Initialize Data (Only called on load)
#---------------------------
def Init():
    global ScriptSettings
    ScriptSettings = Settings(SettingsFile)
    ScriptSettings.Save(SettingsFile)

    global RefreshToken
    global AccessToken
    global TokenExpiration
    if os.path.isfile(RefreshTokenFile):
        with open(RefreshTokenFile) as f:
            content = f.readlines()
        if len(content) > 0:
            data = json.loads(content[0])
            RefreshToken = data["refresh_token"]
            AccessToken = data["access_token"]
            TokenExpiration = datetime.datetime.strptime(data["expiration"], "%Y-%m-%d %H:%M:%S.%f")

    return

#---------------------------
#   [Required] Execute Data / Process messages
#---------------------------
def Execute(data):

    if data.IsChatMessage():
        if ScriptSettings.ResetCommand.lower() in data.Message.lower():
            if Parent.HasPermission(data.User,"Moderator",""):
                length = ScriptSettings.TimerLength
                type = "reset"
                if data.GetParamCount() > 1:
                    length = int(data.GetParam(1))
                    type = "add"
                payload = {
                    "interval": length,
                    "type": type,
                    "redeemedSFXPath": ScriptSettings.RedeemedSFXPath,
                    "redeemedSFXVolume": ScriptSettings.RedeemedSFXVolume/100.0,
                    "finishedSFXPath": ScriptSettings.FinishedSFXPath,
                    "finishedSFXVolume": ScriptSettings.FinishedSFXVolume/100.0
                }
                Parent.BroadcastWsEvent("EVENT_FUCKED_UP",json.dumps(payload, encoding='utf-8-sig'))

    return

#---------------------------
#   [Required] Tick method (Gets called during every iteration even when there is no incoming data)
#---------------------------
def Tick():
    if LastTokenCheck is None:
        return

    if (EventReceiver is None or TokenExpiration < datetime.datetime.now()) and LastTokenCheck + datetime.timedelta(seconds=60) < datetime.datetime.now(): 
        RestartEventReceiver()
        return

    global PlayNextAt
    if PlayNextAt > datetime.datetime.now():
        return

    global CurrentThread
    if CurrentThread and CurrentThread.isAlive() == False:
        CurrentThread = None

    if CurrentThread == None and len(ThreadQueue) > 0:
        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, "Starting new thread. " + str(PlayNextAt))
        CurrentThread = ThreadQueue.pop(0)
        CurrentThread.start()
        
    return

#---------------------------
#   [Optional] Parse method (Allows you to create your own custom $parameters) 
#---------------------------
def Parse(parseString, userid, username, targetid, targetname, message):
    return parseString

#---------------------------
#   [Optional] Reload Settings (Called when a user clicks the Save Settings button in the Chatbot UI)
#---------------------------
def ReloadSettings(jsonData):
    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "Saving settings.")

    try:
        ScriptSettings.__dict__ = json.loads(jsonData)
        ScriptSettings.Save(SettingsFile)

        threading.Thread(target=RestartEventReceiver).start()

        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, "Settings saved successfully")
    except Exception as e:
        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, str(e))

    return

#---------------------------
#   [Optional] Unload (Called when a user reloads their scripts or closes the bot / cleanup stuff)
#---------------------------
def Unload():
    StopEventReceiver()
    return

#---------------------------
#   [Optional] ScriptToggled (Notifies you when a user disables your script or enables it)
#---------------------------
def ScriptToggled(state):
    if state:
        if EventReceiver is None:
            threading.Thread(target=RestartEventReceiver).start()
    else:
        StopEventReceiver()

    return

#---------------------------
#   StartEventReceiver (Start twitch pubsub event receiver)
#---------------------------
def StartEventReceiver():
    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "Starting receiver")

    global EventReceiver
    EventReceiver = TwitchPubSub()
    EventReceiver.OnPubSubServiceConnected += EventReceiverConnected
    EventReceiver.OnRewardRedeemed += EventReceiverRewardRedeemed

    EventReceiver.Connect()

#---------------------------
#   StopEventReceiver (Stop twitch pubsub event receiver)
#---------------------------
def StopEventReceiver():
    global EventReceiver
    try:
        if EventReceiver:
            EventReceiver.Disconnect()
            if ScriptSettings.EnableDebug:
                Parent.Log(ScriptName, "Event receiver disconnected")
        EventReceiver = None

    except:
        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, "Event receiver already disconnected")

#---------------------------
#   RestartEventReceiver (Restart event receiver cleanly)
#---------------------------
def RestartEventReceiver():
    RefreshTokens()
    if InvalidRefreshToken is False:
        if UserID is None:
            GetUserID()
        StopEventReceiver()
        StartEventReceiver()

#---------------------------
#   EventReceiverConnected (Twitch pubsub event callback for on connected event. Needs a valid UserID and AccessToken to function properly.)
#---------------------------
def EventReceiverConnected(sender, e):
    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "Event receiver connected, sending topics for channel id: " + str(UserID))

    EventReceiver.ListenToRewards(UserID)
    EventReceiver.SendTopics(AccessToken)
    return

#---------------------------
#   EventReceiverRewardRedeemed (Twitch pubsub event callback for a detected redeemed channel point reward.)
#---------------------------
def EventReceiverRewardRedeemed(sender, e):
    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "Event triggered: " + str(e.TimeStamp) + " ChannelId: " + str(e.ChannelId) + " Login: " + str(e.Login) + " DisplayName: " + str(e.DisplayName) + " Message: " + str(e.Message) + " RewardId: " + str(e.RewardId) + " RewardTitle: " + str(e.RewardTitle) + " RewardPrompt: " + str(e.RewardPrompt) + " RewardCost: " + str(e.RewardCost) + " Status: " + str(e.Status))

    if e.RewardTitle == ScriptSettings.TwitchRewardName:
        if (ScriptSettings.TwitchRewardActivationType == "Immediate" and "FULFILLED" in e.Status) or (ScriptSettings.TwitchRewardActivationType == r"On Reward Queue Accept/Reject" and "ACTION_TAKEN" in e.Status):
            ThreadQueue.append(threading.Thread(target=RewardRedeemedWorker,args=(ScriptSettings.RedeemedSFXPath, ScriptSettings.RedeemedSFXVolume, ScriptSettings.RedeemedSFXDelay, ScriptSettings.FinishedSFXPath, ScriptSettings.FinishedSFXVolume, ScriptSettings.TimerLength,)))

    return

#---------------------------
#   RewardRedeemedWorker (Worker function to be spun off into its own thread to complete without blocking the rest of script execution.)
#---------------------------
def RewardRedeemedWorker(path, volume, delay, finishedpath, finishedvolume, timerSeconds):
    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, path + " " + str(volume/100.0) + " " + str(delay))

    global PlayNextAt
    PlayNextAt = datetime.datetime.now() + datetime.timedelta(0, delay)

    payload = { 
        "seconds": timerSeconds, 
        "redeemedSFXPath": path,
        "redeemedSFXVolume": volume/100.0,
        "finishedSFXPath": finishedpath,
        "finishedSFXVolume": finishedvolume/100.0
    }

    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, str(payload))
    
    Parent.BroadcastWsEvent('EVENT_NO_FUDGES_REDEEMED', json.dumps(payload, encoding='utf-8-sig'))

#---------------------------
#   RefreshTokens (Called when a new access token needs to be retrieved.)
#---------------------------
def RefreshTokens():
    global RefreshToken
    global AccessToken
    global TokenExpiration
    global LastTokenCheck
    global InvalidRefreshToken
    global InvalidAuthCode

    InvalidRefreshToken = False

    result = None

    try:
        if RefreshToken:
            content = {
	            "grant_type": "refresh_token",
	            "refresh_token": str(RefreshToken)
            }

            result = json.loads(json.loads(Parent.PostRequest("https://api.et-twitch-auth.com/",{}, content, True))["response"])
            if ScriptSettings.EnableDebug:
                Parent.Log(ScriptName, str(content))
        else:
            if ScriptSettings.TwitchAuthCode == "":
                LastTokenCheck = datetime.datetime.now()
                TokenExpiration = datetime.datetime.now()
                Parent.Log(ScriptName, "Access code cannot be retrieved please enter a valid authorization code.")
                InvalidRefreshToken = True
                return

            content = {
                'grant_type': 'authorization_code',
                'code': ScriptSettings.TwitchAuthCode
            }

            result = json.loads(json.loads(Parent.PostRequest("https://api.et-twitch-auth.com/",{}, content, True))["response"])
            if ScriptSettings.EnableDebug:
                Parent.Log(ScriptName, str(content))

        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, str(result))

        RefreshToken = result["refresh_token"]
        AccessToken = result["access_token"]
        TokenExpiration = datetime.datetime.now() + datetime.timedelta(seconds=int(result["expires_in"]) - 300)

        LastTokenCheck = datetime.datetime.now()
        SaveTokens()
    except Exception as e:
        LastTokenCheck = datetime.datetime.now()
        TokenExpiration = datetime.datetime.now()
        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, "Exception: " + str(e.message))
        InvalidRefreshToken = True

#---------------------------
#   GetUserID (Calls twitch's api with current channel user name to get the user id and sets global UserID variable.)
#---------------------------
def GetUserID():
    headers = { 
        "Client-ID": "icyqwwpy744ugu5x4ymyt6jqrnpxso",
        "Authorization": "Bearer " + AccessToken
    }
    result = json.loads(Parent.GetRequest("https://api.twitch.tv/helix/users?login=" + Parent.GetChannelName(), headers))
    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "headers: " + str(headers))
        Parent.Log(ScriptName, "result: " + str(result))
    user = json.loads(result["response"])
    global UserID
    UserID = user["data"][0]["id"]

#---------------------------
#   SaveTokens (Saves tokens and expiration time to a json file in script bin for use on script restart and reload.)
#---------------------------
def SaveTokens():
    data = {
        "refresh_token": RefreshToken,
        "access_token": AccessToken,
        "expiration": str(TokenExpiration)
    }

    with open(RefreshTokenFile, 'w') as f:
        f.write(json.dumps(data))

#---------------------------
#   OpenReadme (Attached to settings button to open the readme file in the script bin.)
#---------------------------
def OpenReadme():
    os.startfile(ReadMe)

#---------------------------
#   GetToken (Attached to settings button to open a page in browser to get an authorization code.)
#---------------------------
def GetToken():
	os.startfile("https://id.twitch.tv/oauth2/authorize?response_type=code&client_id=icyqwwpy744ugu5x4ymyt6jqrnpxso&redirect_uri=https://et-twitch-auth.com/&scope=channel:read:redemptions&force_verify=true")

#---------------------------
#   DeleteSavedTokens (Attached to settings button to allow user to easily delete the tokens.json file and clear out RefreshToken currently in memory so that a new authorization code can be entered and used.)
#---------------------------
def DeleteSavedTokens():
    global RefreshToken
    if os.path.exists(RefreshTokenFile):
        os.remove(RefreshTokenFile)
    RefreshToken = None