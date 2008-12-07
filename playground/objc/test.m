#import <Foundation/Foundation.h>
#import "HelloWorld.h"

int main (int argc, const char * argv[]) {
    NSAutoreleasePool * pool = [[NSAutoreleasePool alloc] init];

    HelloWorld *hw = [[HelloWorld alloc] init];
    [hw autorelease];

    [hw sayHello];

    [pool release];
    return 0;
}
