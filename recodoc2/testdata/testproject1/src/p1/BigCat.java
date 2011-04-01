package p1;

import java.util.List;

import p3.Special;

public class BigCat extends Cat {

	public BigCat(String name) {
		this.name = name;
	}
	
	public BigCat() {
		
	}
	
	@Override
	public int getAge() {
		return super.getAge();
	}
	
	protected float doSomething(int i, String s, byte[] b, List<Special> specials) {
		return 0.0f;
	}
	
}
