package p1;

import java.io.IOException;
import java.util.Collection;
import java.util.List;

public interface Animal {
	
	String getName();
	
	void run();
	
	int getAge();
	
	List<Animal> getChildren();
	
	Collection<Animal> getParents();
	
	void setChildren(List<Animal> children) throws AnimalException, IOException;
	
	void setChildren(List<Animal> children, List<String> names);
	
	String toString();
}
