package p3;

import java.util.Map;

public class Special {

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
}

class Special2<R extends Runnable> {
	public void method1(int a, Special[][] specials) {

	}
	
	public void method2(R r) {
		
	}
}