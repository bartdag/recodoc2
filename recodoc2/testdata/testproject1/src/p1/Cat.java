package p1;

import java.io.IOException;
import java.util.Collection;
import java.util.List;

public class Cat implements Animal {

	protected String name;

	private int age;
	
	private List<Animal> children;
	
	private List<Animal> parents;
	
	@Override
	public String getName() {
		return null;
	}

	@Override
	public void run() {

	}

	@Override
	public int getAge() {
		return 0;
	}

	@Override
	public List<Animal> getChildren() {
		return children;
	}

	@Override
	public Collection<Animal> getParents() {
		return parents;
	}

	@Override
	public void setChildren(List<Animal> children) throws AnimalException,
			IOException {
		this.children = children;
	}

	@Override
	public void setChildren(List<Animal> children, List<String> names) {
		this.children = children;
	}

	@Override
	public boolean equals(Object obj) {
		return super.equals(obj);
	}

	@Override
	public int hashCode() {
		return super.hashCode();
	}

	@Override
	public String toString() {
		return super.toString();
	}

}
