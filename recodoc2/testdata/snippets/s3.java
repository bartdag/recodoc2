/**
 * Hello World!
 */
public class ASnippet extends BSnippet implements CSnippet {
    /**
    * @param arg
    */
    public void m1(String arg) {
        A a = new A("Hello World");
        a.foo().bar(2, true);
        B.baz(a);
        py4j.C.hello("World");
        Object obj = new py4j.internal.D(a);
        // This is a comment!!!
        if (obj != null) {
            System.out.println("Do something!");
        }
    }
}
