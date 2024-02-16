from mojo.subscriber import registerSubscriberEvent

DEFAULT_KEY = 'com.developerName.SomeTool'

if __name__ == '__main__':
    registerSubscriberEvent(
        subscriberEventName=f"{DEFAULT_KEY}.changed",
        methodName="paletteDidChange",
        lowLevelEventNames=[f"{DEFAULT_KEY}.changed"],
        dispatcher="roboFont",
        documentation="Send when the tool palette did change parameters.",
        delay=0,
        # debug=True
    )
