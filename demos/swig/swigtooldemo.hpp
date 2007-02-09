#ifndef SWIGTOOLDEMO_HPP
#define SWIGTOOLDEMO_HPP

#include <string>
#include <iostream>

//this is a inline singleton pattern implementing class.
class TestClass {
    
public:
    static TestClass* instance() {
	if (_instance == 0)
	    _instance = new TestClass();
	return _instance;
    }

    void destroy () { delete _instance; _instance = 0; }
    
protected:
    TestClass() {};
    ~TestClass(){};
    
public:
    void printHelloWorldString() { std::cout << "Hello World from C++" << std::endl; }
    
private:
    static TestClass* _instance;
};


// int test_all() {
//     static TestClass* instance = TestClass::instance();
//     instance->printHelloWorldString();
//     instance->destroy();
//     return 0;
// }

// int test_create() {
//     static TestClass* instance = TestClass::instance();
//     return 0;
// }

// int test_delete() {
//     static TestClass* instance = TestClass::instance();
//     instance->destroy();
//     return 0;
// }


#endif //SWIGTOOLDEMO_HPP
