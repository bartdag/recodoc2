package p3;

import java.io.Serializable;
import java.util.Map;

public class Special implements Runnable, Serializable {

	/**
	 * 
	 */
	private static final long serialVersionUID = -5336115622680983855L;

	public void method1() {
		Runnable runner = new Runnable() {
			
			@Override
			public void run() {
				
			}
		};
	}
	
	class InnerSpecial {
		public void method1(Map<String, Special> map) {

		}
	}
	
	public void run() {
		
	}
}

class Special2<R extends Runnable> {
	public void method1(int a, Special[][] specials) {

	}
	
	public void method2(R r) {
		
	}
}