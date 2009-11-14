#import "HelloWorld.h"

@implementation HelloWorld

- (void)sayHello
{
    NSLog(@"Hello, world, at %@", [NSCalendarDate calendarDate]);
}

@end
